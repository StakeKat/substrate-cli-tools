from typing import List
from subclient.extrinsics import SubstrateExtrinsic, SubstrateExtrinsicParam, SubstrateExtrinsicParamType
from subclient.decoders import SubstrateExtrinsicDecoder
from subclient.utils import get_logger, api_call
from typing import Dict, Optional
from web3 import Web3

logger = get_logger("moonbeamevmdecoder")

abi_map = {
    "0x0000000000000000000000000000000000000800": "ParachainStaking",
    "0x0000000000000000000000000000000000000802": "IERC20"
}


def is_evm_address(address):
    addr = str(address)
    return addr.startswith("0x") and len(addr) == 42


class SubstrateMoonbeamEVMExtrinsicDecoder(SubstrateExtrinsicDecoder):
    _transaction_index_cache: Dict[int, int] = {}
    _abi_cache: Dict[str, Optional[dict]] = {}
    _supported_evm_modules = (
        'Balances',
        'ParachainStaking',
    )
    _supported_functions = (
        'Transact',
    )

    def __init__(self, rpc_uri: str):
        self._rcp_uri = rpc_uri

    @property
    def extrinsic_type(self) -> str:
        return "EVM"

    def _get_abi(self, contract_address: str) -> Optional[dict]:
        import json
        from os import path
        if contract_address not in self._abi_cache.keys():
            abi_name = abi_map[contract_address] if contract_address in abi_map else None
            abi_path = f"abis/{abi_name}.json"
            if abi_name and path.exists(abi_path):
                try:
                    with open(abi_path) as f:
                        self._abi_cache[contract_address] = json.loads(f.read())
                except IOError as e:
                    logger.warning(f"Unable to read abi from {abi_path}: {e}")
                    self._abi_cache[contract_address] = None
            else:
                self._abi_cache[contract_address] = None
        return self._abi_cache[contract_address]

    @api_call
    def _decode_args(self, ex: SubstrateExtrinsic, args: list, events: list) -> List[SubstrateExtrinsic]:
        # Method is not supported
        if ex.function not in self._supported_functions:
            return []
        # Increase TX counter
        self._transaction_index_cache[ex.block] = self._transaction_index_cache.setdefault(ex.block, -1) + 1
        # Go on
        w3 = Web3(Web3.HTTPProvider(self._rcp_uri))
        # Try to get transaction
        try:
            transaction = w3.eth.get_transaction_by_block(ex.block, self._transaction_index_cache[ex.block])
        except (KeyError, ValueError):
            return []
        # Get ABI
        abi_data = None
        contract_address = None
        if 'to' in transaction.keys():
            contract_address = transaction['to']
            abi_data = self._get_abi(contract_address=contract_address)
            if not abi_data:
                return []
        # Get from first
        if 'from' in transaction.keys():
            ex.params.append(SubstrateExtrinsicParam(
                name="from",
                value=transaction['from'],
                param_type=SubstrateExtrinsicParamType.ADDRESS
            ))
        # Check abi
        abi = abi_data['abi']
        name = abi_map[contract_address]
        input = transaction['input']
        contract = w3.eth.contract(address=contract_address, abi=abi)
        # Decode input and replace it on EX
        func_obj, func_params = contract.decode_function_input(input)
        ex.module = name
        ex.function = func_obj.function_identifier.replace('_', ' ').title().replace(' ', '')
        # Check module support
        if ex.module not in self._supported_evm_modules:
            logger.debug(f"Discared EVM module: {ex.module}")
            return []
        # Ignore some calls
        if ex.function in ('CancelDelegationRequest',):
            logger.debug(f"Discared EVM function: {ex.function}")
            return []
        elif ex.module == "Balances" and ex.function != "Transfer":
            logger.debug(f"Discared EVM module: {ex.module}")
            return []
        # Add transaction index
        ex.add_generic(name="evmTransactionIndex", value=str(transaction['transactionIndex']))
        # Functional params
        ex.rm_param("transaction")
        for key in func_params:
            value = func_params[key]
            ptype = SubstrateExtrinsicParamType.GENERIC
            if key in ('amount', 'more', 'less'):
                ptype = SubstrateExtrinsicParamType.AMOUNT
            elif is_evm_address(value):
                ptype = SubstrateExtrinsicParamType.ADDRESS
            ex.params.append(SubstrateExtrinsicParam(name=key, value=value, param_type=ptype))
        return [ex]
