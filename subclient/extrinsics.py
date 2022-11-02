from typing import List, Optional
from enum import Enum
import re


class SubstrateExtrinsicParamType(Enum):
    GENERIC = 0
    AMOUNT = 1
    ADDRESS = 2


class SubstrateExtrinsicParam:
    name: str
    value: str
    param_type: SubstrateExtrinsicParamType

    def __init__(self,
                 name: str,
                 value: object,
                 param_type: SubstrateExtrinsicParamType = SubstrateExtrinsicParamType.GENERIC):
        self.name = name
        self.value = str(value)
        self.param_type = param_type

    @property
    def is_amount(self) -> bool:
        return self.param_type == SubstrateExtrinsicParamType.AMOUNT

    @property
    def is_address(self) -> bool:
        return self.param_type == SubstrateExtrinsicParamType.ADDRESS

    @staticmethod
    def from_amount(value: float, name: str = "amount"):
        return SubstrateExtrinsicParam(name=name, value=value, param_type=SubstrateExtrinsicParamType.AMOUNT)


class SubstrateExtrinsic:
    """
    Generic abstract substrate event
    """
    id: str
    block: int
    module: str
    function: str
    ex_type: str
    params: List[SubstrateExtrinsicParam]

    def __init__(self,
                 id: str,
                 block: int,
                 module: str,
                 function: str,
                 ex_type: str):
        self.id = id
        self.block = block
        self.module = module
        self.function = function
        self.ex_type = ex_type
        self.params = []

    def __str__(self):
        return f"#{self.id}:{self.ex_type}:" \
               f"{self.method}" \
               f"({','.join(x.name + ':' + str(x.param_type).split('.')[1] + '=' + str(x.value) for x in self.params)})"

    def get_param(self, key: str) -> Optional[str]:
        for param in self.params:
            if param.name.lower() == key.lower():
                return param.value
        return None

    def rm_param(self, key: str):
        self.params = [i for i in self.params if i.name.lower() != key.lower()]

    @property
    def amount(self) -> float:
        for param in self.params:
            if param.param_type == SubstrateExtrinsicParamType.AMOUNT:
                return float(param.value)
        return 0.0

    @property
    def method(self) -> str:
        return f"{self.module}.{self.function}"

    def add_amount(self, value: float, name: str = "amount"):
        self.params.append(SubstrateExtrinsicParam(
            name=name,
            value=value,
            param_type=SubstrateExtrinsicParamType.AMOUNT
        ))

    def add_address(self, value: str, name: str = "address"):
        self.params.append(SubstrateExtrinsicParam(
            name=name,
            value=value,
            param_type=SubstrateExtrinsicParamType.ADDRESS
        ))

    def add_generic(self, value: str, name: str):
        self.params.append(SubstrateExtrinsicParam(
            name=name,
            value=value,
            param_type=SubstrateExtrinsicParamType.GENERIC
        ))


class SubstrateExtrinsicFilter:
    address_pattern: str = None
    method_pattern: str = None
    min_amount: int = None
    match_all: bool = True

    def __init__(self,
                 address_pattern: str = None,
                 method_pattern: str = None,
                 min_amount: int = None,
                 match_all: bool = True) -> None:
        super().__init__()
        self.address_pattern = address_pattern
        self.method_pattern = method_pattern
        self.min_amount = min_amount
        self.match_all = match_all

    def __str__(self) -> str:
        return f"[address:{self.address_pattern},method:{self.method_pattern}," \
               f"amount:{self.min_amount},all:{self.match_all}]"

    @property
    def is_flood_filter(self) -> bool:
        """True if filter will return a LOT of events"""
        if self.address_pattern and len(self.address_pattern) > 2:
            return False
        elif self.method_pattern and len(self.method_pattern) > 2:
            return False
        elif self.min_amount and self.min_amount > 100:
            return False
        return True

    def match(self, extrinsic: SubstrateExtrinsic):
        address_match = False
        if not self.address_pattern:
            address_match = True
        else:
            for param in extrinsic.params:
                value = str(param.value).lower()
                if value.startswith("0x") and re.search(self.address_pattern.lower(), value):
                    address_match = True
                    break
        amount_match = not self.min_amount or extrinsic.amount == 0 or extrinsic.amount > self.min_amount
        method_match = not self.method_pattern or re.search(self.method_pattern, extrinsic.method, re.IGNORECASE)
        matches = (address_match, amount_match, method_match)
        return all(matches) if self.match_all else any(matches)
