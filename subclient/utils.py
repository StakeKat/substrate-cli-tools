from functools import wraps
from json import JSONDecodeError
from websocket import WebSocketException


def get_logger(name: str):
    import logging
    return logging.getLogger(f"subclient.{name}")


logger = get_logger("utils")


def api_call(func):
    # noinspection PyProtectedMember,PyStatementEffect
    @wraps(func)
    def _decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (
                BrokenPipeError,
                AttributeError,
                OSError,
                JSONDecodeError,
                WebSocketException
        ) as e:
            from time import sleep
            import traceback
            # traceback.print_exc()
            logger.warning(f"#### Endpoing disconnected {e} retrying")
            # Close websocket
            # Clear instance so its recreated
            if hasattr(args[0], "_api_instance"):
                if args[0]._api_instance and hasattr(args[0]._api_instance, "close"):
                    # noinspection PyBroadException
                    try:
                        args[0]._api_instance.close()
                    except:
                        pass
                args[0]._api_instance = None
            sleep(5)
            return func(*args, **kwargs)

    return _decorator
