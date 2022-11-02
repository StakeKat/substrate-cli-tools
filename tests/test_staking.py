from subclient.moonbeam import MoonbeamClient
from logging import getLogger

cache_path = ".pytest_cache/cw"
logger = getLogger("test")


def get_client() -> MoonbeamClient:
    from subclient import get_client
    return get_client("moonbeam", cache_path)


def test_moonbeam_collator_rewards():
    client = get_client()
    # Get current staking APR
    pool_size = client.candidate_pool_size
    assert pool_size > 48
    assert pool_size < 1024
    logger.debug(f"{client.total_inflation}")
    candidate_daily_rewards = int(client.total_inflation / 5.0 / pool_size / 365.0)
    assert candidate_daily_rewards < 1000
    assert candidate_daily_rewards > 100


def test_moonbeam_delegator_state():
    client = get_client()
    state = client.get_delegator_state(address="0xF5018bAc9D3c9223a02F8F861C97EBFe2FBec78D", block_nr=1294492)
    assert state.total_revoked > 0
