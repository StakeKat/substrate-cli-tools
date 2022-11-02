from subclient.cache import CacheWrapper, cache_call
from time import sleep

cache_path = ".pytest_cache/cw"


class CacheTest:
    _cache: CacheWrapper

    def __init__(self) -> None:
        import shutil
        super().__init__()
        shutil.rmtree(cache_path, ignore_errors=True)
        self._cache = CacheWrapper(cache_path=cache_path)

    @cache_call(expire=2)
    def get_random(self, start=10000, end=99999) -> int:
        from random import choice
        return choice(range(start, end))

    @property
    @cache_call(expire=2)
    def random(self) -> int:
        from random import randint
        return randint(1, 1000000)


def test_cache_decorator_skip_cache():
    ct = CacheTest()
    r1 = ct.get_random(skip_cache=True)
    r2 = ct.get_random(skip_cache=True)
    assert r1 != r2


def test_cache_decorator_expire():
    ct = CacheTest()
    r1 = ct.get_random(start=100000, end=999999)
    sleep(3)
    r2 = ct.get_random(start=100000, end=999999)
    assert r1 != r2


def test_cache_decorator_args_hashing():
    ct = CacheTest()
    r1 = ct.get_random(start=100000, end=999999)
    r2 = ct.get_random(start=100000, end=999999)
    assert r1 == r2
    r3 = ct.get_random(start=100000, end=999998)
    assert r3 != r2


def test_cache_get():
    ct = CacheTest()
    ct._cache.set(key="test", value=10)
    r = ct._cache.get(key="test")
    assert r == 10


def test_cache_property():
    ct = CacheTest()
    r1 = ct.random
    assert r1 > 0
    r2 = ct.random
    assert r1 == r2


def test_cache_client_method():
    from time import time
    from subclient import get_client, MoonbeamClient
    client: MoonbeamClient = get_client("moonbeam", cache_path)
    s1 = time()
    client.get_candidate_pool()
    d1 = time() - s1
    s2 = time()
    client.get_candidate_pool()
    d2 = time() - s2
    assert d2 < d1
