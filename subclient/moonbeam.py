import random

from substrateinterface import KeypairType

from subclient.decoders import SubstrateExtrinsicDecoder
from subclient.extrinsics import SubstrateExtrinsic, SubstrateExtrinsicParam
from subclient.decoders import SubstrateMoonbeamEVMExtrinsicDecoder, SubstrateMoonbeamValidationExtrinsicDecoder
from subclient import SubstrateEndpoint
from subclient.core import SubstrateClient
from typing import Optional, List, Dict, Any
from subclient.utils import get_logger, api_call
from subclient.cache import cache_call

logger = get_logger("moonbeam")


class SubstrateStakingRound:
    """
    Collator round
    """
    number: int
    first: int
    length: int

    def __init__(self, number: int, first: int, length: int) -> None:
        self.number = number
        self.first = first
        self.length = length


class SubstrateStakingCandidateDelegation:
    address: str
    collator: str
    amount: float
    reward: float = None
    revoke_amount: float = 0
    revoke_round: int = None
    revoke_action: str = None

    def __init__(self,
                 address: str,
                 collator: str,
                 amount: float):
        self.address = address
        self.collator = collator
        self.amount = amount


class SubstrateStakingDelegator:
    """
    Delegator
    """
    address: str
    delegations: List[SubstrateStakingCandidateDelegation] = []

    def __init__(self, address: str):
        self.address = address

    @property
    def total_delegated(self):
        return sum([x.amount for x in self.delegations])

    @property
    def total_revoked(self):
        return sum([x.revoke_amount for x in self.delegations])

    def get_delegation(self, collator: str) -> Optional[SubstrateStakingCandidateDelegation]:
        for x in self.delegations:
            if x.collator.lower() == collator.lower():
                return x
        return None


class SubstrateStakingCandidate:
    """
    Collator
    """
    address: str
    total_counted: float
    active: bool
    selected: bool
    rank: int
    rank_last_selected_at: float
    rank_prev_at: float
    rank_next_at: float
    total_selected: int
    total_active: int

    def __init__(self,
                 address: str,
                 total_counted: float,
                 active: bool,
                 selected: bool,
                 rank: int,
                 rank_last_selected_at: float,
                 rank_prev_at: float,
                 rank_next_at: float,
                 total_selected: int,
                 total_active: int):
        self.address = address
        self.total_counted = total_counted
        self.active = active
        self.selected = selected
        self.rank = rank
        self.rank_last_selected_at = rank_last_selected_at
        self.rank_prev_at = rank_prev_at
        self.rank_next_at = rank_next_at
        self.total_selected = total_selected
        self.total_active = total_active


class MoonbeamClient(SubstrateClient):
    _evm_extrinsic_decoder: SubstrateMoonbeamEVMExtrinsicDecoder
    _validation_decoder: SubstrateMoonbeamValidationExtrinsicDecoder = None

    def __init__(self, endpoint: SubstrateEndpoint, cache_path: str):
        super().__init__(endpoint, cache_path)
        rcp_uri = random.choice(endpoint.options["rpc_endpoints"])
        self._evm_extrinsic_decoder = SubstrateMoonbeamEVMExtrinsicDecoder(rcp_uri)
        self._validation_decoder = SubstrateMoonbeamValidationExtrinsicDecoder(endpoint)

    def _get_extrinsic_decoder(self, pallet: str, method: str) -> SubstrateExtrinsicDecoder:
        if pallet == "Ethereum":
            return self._evm_extrinsic_decoder
        elif pallet == "ParachainSystem":
            return self._validation_decoder
        return super()._get_extrinsic_decoder(pallet, method)

    def _should_decode_extrinsic(self, pallet: str, method: str) -> bool:
        if pallet in ("Ethereum", "ParachainStaking", "ParachainSystem"):
            return True
        return super()._should_decode_extrinsic(pallet, method)

    @api_call
    def _decode_delegator_state(self, data, block_hash) -> SubstrateStakingDelegator:
        # First create delegator
        delegations = {}
        # Then get all delegations and store by collator
        for delegation in data['delegations']:
            delegations[delegation['owner']] = SubstrateStakingCandidateDelegation(
                address=data['id'],
                collator=delegation['owner'],
                amount=self.token_humanize(delegation['amount'])
            )
            # Get revokes
            cache_key = f"candidate_scheduled_requests_{delegation['owner']}_{block_hash}"
            requests_data = self._cache.get(cache_key)
            if requests_data is None:
                try:
                    requests_data = self._api.query(
                        module='ParachainStaking',
                        storage_function='DelegationScheduledRequests',
                        params=[delegation['owner']],
                        block_hash=block_hash
                    ).value
                    self._cache.set(cache_key, requests_data, expire=300)
                except Exception as e:
                    logger.warning(f"Unable to get delegations: {e}")
            for request in (requests_data if requests_data else []):
                if request['delegator'] == data['id']:
                    action = list(request['action'].items())[0]
                    delegations[delegation['owner']].revoke_round = request['when_executable']
                    delegations[delegation['owner']].revoke_amount = self.token_humanize(action[1])
                    delegations[delegation['owner']].revoke_action = action[0]
                    break
        # Done
        result = SubstrateStakingDelegator(address=data['id'])
        result.delegations = list(delegations.values())
        return result

    def _on_extrinsic_decoded(self, ex: SubstrateExtrinsic, context: Dict[str, Any]):
        super()._on_extrinsic_decoded(ex, context)
        # Delegation revoked, add amount
        amount = None
        if ex.function in ("ScheduleRevokeDelegation",):
            candidate = ex.get_param("candidate")
            delegator = ex.get_param("from")
            amount = self.get_delegation_amount(
                delegator_address=delegator,
                collator_address=candidate,
            )
        # Delegation action executed, add amount on previous block as this might be gone
        elif ex.function in ("ExecuteDelegationRequest",):
            candidate = ex.get_param("candidate")
            delegator = ex.get_param("delegator")
            amount = self.get_delegation_amount(
                delegator_address=delegator,
                collator_address=candidate,
                block_nr=ex.block - 5,
                skip_cache=True
            )
        if amount:
            ex.params.append(SubstrateExtrinsicParam.from_amount(amount))
        # Add collator info
        candidate_id = ex.get_param("candidate")
        if candidate_id:
            if "candidate_pool" not in context:
                context['candidate_pool'] = self.get_candidate_pool(skip_cache=True)
            candidate = next((x for x in context['candidate_pool'] if x.address.lower() == candidate_id.lower()), None)
            if candidate:
                ex.add_amount(name="candidateBacking", value=candidate.total_counted)
                ex.add_generic(name="candidatePoolSize", value=f"{candidate.total_selected}/{candidate.total_active}")
                ex.add_generic(
                    name="candidateRank",
                    value=f"{candidate.rank} {'selected' if candidate.selected else 'waiting'}"
                )

    @property
    def total_inflation(self) -> float:
        return self.total_issuance * 0.05

    @property
    @api_call
    def last_round(self) -> SubstrateStakingRound:
        logger.debug("get_last_round")
        result = self._api.query(
            module='ParachainStaking',
            storage_function='Round'
        ).value
        return SubstrateStakingRound(
            number=result['current'],
            length=result['length'],
            first=result['first']
        )

    @property
    def delegation_bond_less_delay(self):
        return self._api.get_constant(
            module_name='ParachainStaking',
            constant_name='DelegationBondLessDelay'
        ).value

    @api_call
    def get_candidate_points(self, address, round_nr: int = 0) -> int:
        expire = 300
        last_round = self.last_round
        if round_nr > 0:
            expire = None
        else:
            round_nr = last_round.number
        cache_key = f"candidate_points_{address}_{round_nr}"
        result = self._cache.get(cache_key)
        if result is None:
            block_hash = None
            if round_nr < last_round.number:
                target_block = self.last_block_number - (last_round.length * (last_round.number - round_nr - 1))
                block_hash = self._api.get_block_hash(target_block)
            result = self._api.query(
                module='ParachainStaking',
                storage_function='AwardedPts',
                params=[round_nr, address],
                block_hash=block_hash
            ).value / 20
            self._cache.set(key=cache_key, value=result, expire=expire)
        return result

    @api_call
    def get_delegator_state_list(self) -> List[SubstrateStakingDelegator]:
        result = []
        page_size = 250
        data = self._api.query_map(
            module='ParachainStaking',
            storage_function='DelegatorState',
            page_size=page_size
        )
        records = data.records
        while True:
            for record in records:
                result.append(self._decode_delegator_state(record[1].value))
            if len(records) == page_size:
                records = data.retrieve_next_page(data.last_key)
            else:
                break
        return result

    @api_call
    def get_delegator_state(self,
                            address,
                            block_nr: int = None,
                            skip_cache: bool = False) -> Optional[SubstrateStakingDelegator]:
        cache_key = f"delegator_state_{address}"
        result = self._cache.get(cache_key)
        if result is None or skip_cache:
            logger.debug(f"get_delegator_state_{address}")
            block_hash = None
            if block_nr:
                block_hash = self._api.get_block_hash(block_id=block_nr)
            data = self._api.query(
                module='ParachainStaking',
                storage_function='DelegatorState',
                params=[address],
                block_hash=block_hash
            ).value
            # Is delegator gone?
            if not data:
                return None
            result = self._decode_delegator_state(data, block_hash)
            # Shorter cache if delegator has revokes
            if not block_nr:
                self._cache.set(key=cache_key, value=result, expire=3600)
        return result

    @property
    def crypto_type(self) -> KeypairType:
        return KeypairType.ECDSA

    @property
    def staking_apr(self) -> float:
        collators = self.get_candidate_pool()
        total_staked = sum([x.total_counted for x in collators if x.selected])
        return 1.0 / total_staked * self.total_inflation / 2

    def get_candidate(self, address: str, round_nr: int = 0, skip_cache=False) -> Optional[SubstrateStakingCandidate]:
        pool = self.get_candidate_pool(round_nr=round_nr, skip_cache=skip_cache)
        for candidate in pool:
            if candidate.address.lower() == address.lower():
                return candidate
        return None

    def get_delegation_amount(self,
                              delegator_address: Optional[str],
                              collator_address: Optional[str],
                              block_nr: int = None,
                              skip_cache: bool = False) -> float:
        if collator_address and delegator_address:
            state = self.get_delegator_state(address=delegator_address, block_nr=block_nr, skip_cache=skip_cache)
            delegation = state.get_delegation(collator=collator_address) if state else None
            if delegation:
                return delegation.amount
        return 0.0

    @cache_call(expire=600)
    @api_call
    def get_candidate_delegations(self, address: str) -> List[SubstrateStakingCandidateDelegation]:
        logger.debug(f"get_candidate_delegations_{address}")
        top_delegations = self._api.query(
            module='ParachainStaking',
            storage_function='TopDelegations',
            params=[address]
        ).value['delegations']
        if top_delegations:
            result = [SubstrateStakingCandidateDelegation(
                address=x['owner'],
                collator=address,
                amount=self.token_humanize(x['amount'])
            ) for x in top_delegations]
            return result
        else:
            return []

    @api_call
    def get_candidate_pool(self, round_nr: int = 0, skip_cache: bool = False) -> List[SubstrateStakingCandidate]:
        block_hash = None
        # Round has been provided calculate state at a given round
        expire = 300
        cache_key = f"candidate_pool_{round_nr}"
        if round_nr > 0:
            expire = None
            last_round = self.last_round
            last_block = self.last_block_number
            target_block = last_block - ((last_round.number - round_nr) * last_round.length)
            block_hash = self._api.get_block_hash(target_block)
        result = self._cache.get(cache_key)
        if result is None or skip_cache:
            logger.info(f"Loading candidate pool round {cache_key}")
            # Query info
            candidate_info = self._api.query_map(
                module='ParachainStaking',
                storage_function='CandidateInfo',
                params=[],
                block_hash=block_hash
            ).records
            pool = [x[1].value for x in candidate_info]
            for index, x in enumerate(candidate_info):
                pool[index]['id'] = x[0].value
                pool[index]['top_delegations'] = []
            # Selected
            selected = self._api.query(
                module='ParachainStaking',
                storage_function='SelectedCandidates',
                block_hash=block_hash
            ).value
            # Sort by amount and rank
            pool.sort(key=lambda x: x['total_counted'], reverse=True)
            for position, candidate in enumerate(pool, start=1):
                candidate['rank'] = position
            # Get last in ranking
            candidate_last = pool[len(selected) - 1]
            # To object
            result = [SubstrateStakingCandidate(
                address=x['id'],
                total_counted=self.token_humanize(x['total_counted']),
                active=x['status'] == "Active",
                selected=x['id'] in selected,
                rank=x['rank'],
                rank_last_selected_at=self.token_humanize(x['total_counted'] - candidate_last['total_counted']),
                rank_prev_at=self.token_humanize(x['total_counted'] - pool[max(0, i - 1)]['total_counted']),
                rank_next_at=self.token_humanize(x['total_counted'] - pool[min(len(pool) - 1, i + 1)]['total_counted']),
                total_selected=len(selected),
                total_active=len(pool),
            ) for i, x in enumerate(pool)]
            self._cache.set(key=cache_key, value=result, expire=expire)
        return result

    def delegator_bond_more(self, delegator: str, collator: str, amount: float):
        call_args = {
            'call_module': 'ParachainStaking',
            'call_function': 'delegator_bond_more',
            'call_args': {
                'candidate': f"{collator}",
                'more': f"{self.token_dehumanize(amount)}"
            }
        }
        logger.info(f"DelegatorBondMore: {call_args}")
        self._execute_proxy_call(address=delegator, call_args=call_args, proxy_type="Staking")
