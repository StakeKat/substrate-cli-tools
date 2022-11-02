from typing import List
from subclient.extrinsics import SubstrateExtrinsic
from subclient.decoders import SubstrateExtrinsicDecoder
from subclient.utils import api_call
from substrateinterface import SubstrateInterface
from threading import Lock


class SubstrateMoonbeamValidationExtrinsicDecoder(SubstrateExtrinsicDecoder):
    _endpoint = None
    _lock: Lock = Lock()
    _api_instance: SubstrateInterface = None

    # We cannot reference Endpoint type due to an issue in circular import
    def __init__(self, endpoint) -> None:
        super().__init__()
        self._endpoint = endpoint

    @property
    def _api(self) -> SubstrateInterface:
        with self._lock:
            if not self._api_instance:
                self._api_instance = SubstrateInterface(url=self._endpoint.random_wss_uri)
            return self._api_instance

    @api_call
    def _decode_args(self, ex: SubstrateExtrinsic, args: list, events: list) -> List[SubstrateExtrinsic]:
        block_hash = self._api.get_block_hash(ex.block)
        receipt = self._api.get_events(block_hash=block_hash)
        collator = None
        result = []
        for r in receipt:
            event = r['event'].value
            pallet = event['module_id']
            function = event['event_id']
            if ((pallet == "MoonbeamOrbiters" and function == "OrbiterRewarded")
                    or (pallet == "ParachainStaking" and function == "Rewarded")):
                dest_addr = event['attributes'][0]
                amount = event['attributes'][1]
                if not collator:
                    collator = dest_addr
                event_ex = SubstrateExtrinsic(
                    id=ex.id,
                    block=ex.block,
                    module=pallet,
                    function=function,
                    ex_type=ex.ex_type
                )
                event_ex.add_amount(amount)
                event_ex.add_address(dest_addr)
                if collator and collator != dest_addr:
                    event_ex.add_address(collator, name="collator")
                result.append(event_ex)
        return result
