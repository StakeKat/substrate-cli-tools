from subclient.utils import get_logger
from diskcache import Cache
from functools import wraps
from hashlib import md5

logger = get_logger("cache")


class CacheWrapper:
    _cache: Cache

    def __init__(self, cache_path: str) -> None:
        super().__init__()
        self._cache_path = cache_path
        self._cache = Cache(cache_path) if cache_path else None

    def get(self, key: str):
        return self._cache.get(key) if self._cache_path else None

    def set(self, key: str, value: object, expire=None, tag=None) -> bool:
        write_result = self._cache.set(key, value, expire=expire, tag=tag) if self._cache_path else False
        logger.debug(f"Cache set {key}={value} expire:{expire} tag:{tag} success:{write_result}")
        return write_result


def cache_call(expire: int = 0):
    def cache_call_func(func):
        """
        This decorator will do the following:
        - Add a skip_cache named argument to all functions, when set to True cache will not be used
        - Use function name and args to create a cache key
        - Use class at args[0] and look for a _cache object, if found use it to write/read result
        """

        # noinspection PyProtectedMember,PyStatementEffect
        @wraps(func)
        def _decorator(*args, **kwargs):
            # Check for skip cache param
            if kwargs and "skip_cache" in kwargs.keys():
                skip_cache = kwargs['skip_cache']
                del kwargs['skip_cache']
                # We have been asked to skip cache, so do it
                if skip_cache:
                    return func(*args, **kwargs)
            # Check for cache instance
            if hasattr(args[0], "_cache") and isinstance(args[0]._cache, CacheWrapper):
                cache: CacheWrapper = args[0]._cache
                cache_args = "_".join([str(x) for x in args[1:]] + [f"{k}={v}" for k, v in kwargs.items()])
                cache_key = func.__name__.replace("get_", "") + "_" + md5(cache_args.encode()).hexdigest()
                result = cache.get(key=cache_key)
                if result is None:
                    result = func(*args, **kwargs)
                    cache.set(key=cache_key, value=result, expire=expire)
                    return result
                else:
                    logger.debug(f"cache hit:{cache_key} args:{cache_args}")
                    return result
            else:
                logger.warning(f"cannot find cache instance in self {args[0]}")
                return func(*args, **kwargs)

        return _decorator

    return cache_call_func
