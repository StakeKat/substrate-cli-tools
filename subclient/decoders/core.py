from typing import List
from subclient.extrinsics import SubstrateExtrinsic, SubstrateExtrinsicParam, SubstrateExtrinsicParamType


class SubstrateExtrinsicDecoder:

    @property
    def extrinsic_type(self) -> str:
        return "Substrate"

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def _decode_args(self, ex: SubstrateExtrinsic, args: list, events: list) -> List[SubstrateExtrinsic]:
        return [ex]

    def decode(self, block_nr: int, index: int, extrinsic, events: list) -> List[SubstrateExtrinsic]:
        module = extrinsic["call"]["call_module"]
        function = extrinsic["call"]["call_function"]
        ex = SubstrateExtrinsic(
            block=block_nr,
            id=f"{block_nr}-{index}",
            module=module,
            function=function.replace('_', ' ').title().replace(' ', ''),
            ex_type=self.extrinsic_type
        )
        # Signed from
        if 'address' in extrinsic:
            ex.params.append(SubstrateExtrinsicParam(
                name="from",
                value=extrinsic['address'],
                param_type=SubstrateExtrinsicParamType.ADDRESS)
            )
        # Basic params
        args = extrinsic['call']['call_args']
        for param in args:
            name = param['name']
            value = param['value']
            param_type = param['type']
            # Types that are amounts
            if param_type in ('Balance', 'BalanceOf') and str(value).isdigit():
                ex.add_amount(name=name, value=float(value))
            elif param_type in ('LookupSource',) or str(value).startswith("0x"):
                ex.add_address(name=name, value=str(value))
            else:
                ex.add_generic(name=name, value=value)
        # Decode specific args if any
        return self._decode_args(ex=ex, args=args, events=events)
