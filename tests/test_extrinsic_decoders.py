from subclient.moonbeam import MoonbeamClient
from logging import getLogger

cache_path = ".pytest_cache/cw"
logger = getLogger("test")


def get_client() -> MoonbeamClient:
    from subclient import get_client
    return get_client("moonbeam", cache_path)


def test_balances():
    client = get_client()
    r = client.get_extrinsics(start_block=368304, end_block=368304)
    assert len(r) == 1
    ex = r[0]
    assert ex.amount > 0


def test_moonbeam_delegate_more():
    client = get_client()
    r = client.get_extrinsics(start_block=171260, end_block=171260)
    assert len(r) == 1
    ex = r[0]
    logger.info(str(ex))
    assert ex.amount > 0


def test_moonbeam_evm_delegation_increased():
    client = get_client()
    r = client.get_extrinsics(start_block=389227, end_block=389227)
    assert len(r) == 2
    ex = r[1]
    logger.info(str(ex))
    assert ex.ex_type == "EVM"
    assert ex.amount > 0


def test_moonbeam_evm_revoke():
    client = get_client()
    r = client.get_extrinsics(start_block=411677, end_block=411677)
    assert len(r) == 1
    ex = r[0]
    logger.info(str(ex))
    assert ex.ex_type == "EVM"
    assert ex.amount > 40000


def test_moonbeam_execute_revoke():
    r = get_client().get_extrinsics(start_block=381188, end_block=381188)
    assert len(r) == 1
    ex = r[0]
    logger.info(str(ex))
    assert ex.get_param("delegator")
    assert ex.amount > 0


def test_moonbeam_evm_from():
    addr = "0xb01744745fbBebE6A0Da674F8f45fD1e14D5B488"
    client = get_client()
    r = client.get_extrinsics(start_block=333456, end_block=333456)
    assert r[0].get_param("from") == addr


def test_amount_filter():
    from subclient.extrinsics import SubstrateExtrinsicFilter
    client = get_client()
    r = client.get_extrinsics(start_block=403619, end_block=403619)
    assert len(r) > 0
    ex = r[0]
    assert ex.amount > 10000
    filter = SubstrateExtrinsicFilter(method_pattern="staking", min_amount=5000)
    assert filter.match(ex)
