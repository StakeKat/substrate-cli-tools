__app__ = "subtools"
__version__ = "0.0.1"


def get_logger(name: str):
    import logging
    return logging.getLogger(f"{__app__}.{name}")
