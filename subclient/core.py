from substrateinterface import SubstrateInterface, Keypair, KeypairType

from subclient.cache import CacheWrapper, cache_call
from subclient.extrinsics import SubstrateExtrinsic, SubstrateExtrinsicParamType
from subclient.utils import api_call, get_logger
from subclient.decoders import SubstrateExtrinsicDecoder
from threading import Lock
from typing import List, Optional, Tuple, Dict, TypeVar, Type, Generic, Any
from abc import ABC, abstractmethod

logger = get_logger("core")

T = TypeVar('T', bound='subclient')


class SubstrateEndpoint(Generic[T]):
    chain_id: str
    wss_endpoints: List[str]
    client_type: Type[T]
    options: Dict

    def __init__(self, chain_id: str, wss_endpoints: List[str], client_type: Type[T], options: Dict = None) -> None:
        self.chain_id = chain_id
        self.wss_endpoints = wss_endpoints
        self.client_type = client_type
        if options:
            self.options = options
        else:
            self.options = {}

    def get_client(self, cache_path: str) -> T:
        return self.client_type(endpoint=self, cache_path=cache_path)

    @property
    def random_wss_uri(self) -> str:
        from random import choice
        return f"wss://{choice(self.wss_endpoints)}"


class SubstrateBlockHeader:
    number: int
    hash: str

    def __str__(self):
        return f"#{self.number} hash:{self.hash}"


class SubstrateIdentity:
    """
    Substrate identity
    """
    address: str
    display: str

    def __init__(self, address, display):
        self.address = address
        self.display = display

    def __str__(self):
        return f"{self.display if self.display else self.address}"


class SubstrateClient(ABC):
    _endpoint: SubstrateEndpoint
    _api_instance: SubstrateInterface = None
    _lock: Lock = Lock()
    _cache: CacheWrapper
    _abi_cache: Dict[str, Optional[Tuple[str, dict]]] = {}
    _default_extrinsic_decoder = SubstrateExtrinsicDecoder()

    def __init__(self, endpoint: SubstrateEndpoint, cache_path: str):
        self._endpoint = endpoint
        self._cache = CacheWrapper(cache_path)

    @property
    def _api(self) -> SubstrateInterface:
        with self._lock:
            if not self._api_instance:
                self._api_instance = SubstrateInterface(url=self._endpoint.random_wss_uri)
            return self._api_instance

    @cache_call
    @api_call
    def _get_block_hash(self, block_number) -> str:
        logger.debug(f"get_block_hash {block_number}")
        return self._api.get_block_header(block_number=block_number)['header']['hash']

    # noinspection PyUnusedLocal
    def _get_extrinsic_decoder(self, pallet: str, method: str) -> SubstrateExtrinsicDecoder:
        return self._default_extrinsic_decoder

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _should_decode_extrinsic(self, pallet: str, method: str) -> bool:
        return pallet == "Balances"

    def _on_extrinsic_decoded(self, ex: SubstrateExtrinsic, context: Dict[str, Any]):
        for param in ex.params:
            if param.param_type == SubstrateExtrinsicParamType.AMOUNT:
                param.value = self.token_humanize(param.value)

    @api_call
    def _execute_proxy_call(self, address, call_args, proxy_type: str):
        keypair = self.get_keypair()
        logger.info(f"Execute on behalf of {address} with proxy {keypair.ss58_address}")
        # Change mapping
        call = self._api.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': address,
                'force_proxy_type': proxy_type,
                'call': call_args,
            }
        )
        # Make and call
        extrinsic = self._api.create_signed_extrinsic(call=call, keypair=keypair)
        receipt = self._api.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        logger.info("extrinsic '{}' sent and included in block '{}' fee '{:.2f}'".format(
            receipt.extrinsic_hash,
            receipt.block_hash,
            float(receipt.total_fee_amount) / (10 ** self._api.token_decimals)
        ))

    @property
    @api_call
    def last_block_number(self) -> int:
        head = self._api.get_chain_finalised_head()
        return self._api.get_block_number(block_hash=head)

    @property
    def block_duration(self) -> float:
        return 12.2

    @property
    def id(self) -> str:
        return self._endpoint.chain_id

    @property
    @api_call
    def symbol(self):
        return self._api.token_symbol

    @property
    @cache_call(expire=3600)
    @api_call
    def candidate_pool_size(self) -> int:
        logger.debug(f"get_candidate_pool_size")
        return self._api.query(
            module='ParachainStaking',
            storage_function='TotalSelected',
            params=[]
        ).value

    @property
    @abstractmethod
    def total_inflation(self) -> float:
        return 0.0

    @property
    def crypto_type(self) -> KeypairType:
        return KeypairType.SR25519

    @property
    @cache_call(expire=3600)
    @api_call
    def total_issuance(self) -> float:
        logger.debug(f"get_total_issuance")
        return self.token_humanize(self._api.query(
            module='Balances',
            storage_function='TotalIssuance',
            params=[]
        ).value)

    @cache_call(expire=3600)
    @api_call
    def get_identity(self, address) -> SubstrateIdentity:
        logger.debug(f"get_identity {address}")
        result = None
        try:
            result = self._api.query(
                module='Identity',
                storage_function='IdentityOf',
                params=[address]
            ).value
        # int object not subscriptable in library
        except TypeError:
            pass
        if not result:
            # Store a dummy value
            result = {'info': {}}
        return SubstrateIdentity(
            address=address,
            display=result['info']['display']['Raw'] if 'display' in result['info'] else address
        )

    @api_call
    def token_humanize(self, value) -> float:
        return float(value) / (10 ** self._api.token_decimals)

    @api_call
    def token_dehumanize(self, value) -> int:
        return int(float(value) * (10 ** self._api.token_decimals))

    def get_keypair(self, seed=None) -> Keypair:
        import base64
        if not seed:
            import os
            skey = f"S_{self._endpoint.chain_id}".upper()
            if skey not in os.environ:
                raise NameError(f"Unable to find {skey} in environ")
            # Create keypair
            seed = base64.b64decode(os.environ[skey]).decode("utf-8").strip()
        keypair = Keypair.create_from_mnemonic(seed, crypto_type=self.crypto_type)
        return keypair

    @cache_call(expire=60)
    @api_call
    def get_free_balance(self, address, skip_cache=False) -> float:
        logger.debug(f"get_free_balance {address}")
        balance = self._api.query(
            module='System',
            storage_function='Account',
            params=[address]
        ).value['data']
        print(balance)
        return self.token_humanize(balance['free'] - balance['misc_frozen'])

    def close(self):
        try:
            self._api.close()
        except Exception as e:
            logger.warning(f"Unable to close connection {e}")
            pass

    @api_call
    def get_extrinsics(self,
                       start_block: int = None,
                       end_block: int = None,
                       use_cache: bool = False
                       ) -> List[SubstrateExtrinsic]:
        """
        :param int start_block: first block to look for, None for latest
        :param int end_block: last block to look for, None for latest
        :param bool use_cache: use the internal cache, it might use a lot of space when monitoring
        """
        last_nr = self.last_block_number
        start_nr = start_block if start_block is not None and start_block <= last_nr else last_nr
        end_nr = end_block if end_block is not None and end_block >= start_nr else last_nr
        result = []
        decoding_context = {}
        for block_nr in range(start_nr, end_nr + 1):
            # Cache request
            if use_cache:
                cached_result = self._cache.get(f"extrinsics_{block_nr}")
                if cached_result:
                    return cached_result
            # Skip cache
            block_hash = self._api.get_block_hash(block_nr)
            extrinsics = self._api.get_block(block_hash=block_hash)['extrinsics']
            for index, extrinsic in enumerate(extrinsics):
                pallet = extrinsic.value["call"]["call_module"]
                method = extrinsic.value["call"]["call_function"]
                if self._should_decode_extrinsic(pallet=pallet, method=method):
                    decoder = self._get_extrinsic_decoder(pallet=pallet, method=method)
                    receipt = self._api.retrieve_extrinsic_by_identifier(f"{block_nr}-{index}")
                    # Only process events with no errors
                    if not receipt.error_message:
                        decoded_extrinsics = decoder.decode(
                            block_nr=block_nr,
                            index=index,
                            extrinsic=extrinsic.value,
                            events=receipt.triggered_events
                        )
                        for decoded_extrinsic in decoded_extrinsics:
                            self._on_extrinsic_decoded(decoded_extrinsic, decoding_context)
                            result.append(decoded_extrinsic)
            # Store cache
            if use_cache:
                self._cache.set(f"extrinsics_{block_nr}", result)
        return result

    def transfer_batch(self, source: str, dest_value_map: List[Tuple[str, float]]):
        """
        :param str source: address to point proxy to
        :param dest_value_map: a list of address/amount tuples
        """
        calls = [self._api.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': f"{x[0]}",
                'value': f"{self.token_dehumanize(x[1])}"
            }
        ) for x in dest_value_map]
        call_args = self._api.compose_call(
            call_module='Utility',
            call_function='batch',
            call_params={
                'calls': [x.value for x in calls]
            }
        ).value
        logger.info(f"Transfer: {call_args}")
        self._execute_proxy_call(address=source, call_args=call_args, proxy_type="Balances")

    def transfer(self, source: str, dest: str, amount: float):
        """
        :param str source: address to point proxy to
        :param dest: destination address
        :param amount: amount to transfer
        """
        call = self._api.compose_call(
            call_module='Balances',
            call_function='transfer',
            call_params={
                'dest': f"{dest}",
                'value': f"{self.token_dehumanize(amount)}"
            }
        )
        logger.info(f"Transfer: {call.value}")
        self._execute_proxy_call(address=source, call_args=call.value, proxy_type="Balances")
