import os
from typing import Optional

from subclient import get_client
from subclient.core import SubstrateClient, SubstrateExtrinsic
from subtools import get_logger

logger = get_logger("cli")


def chain_extrinsic_to_text(client: SubstrateClient, extrinsic: SubstrateExtrinsic):
    msg = f'#{extrinsic.id}:{extrinsic.ex_type}:{extrinsic.method}('
    params = []
    for param in extrinsic.params:
        if param.is_amount:
            value = f"{float(param.value):.2f}{client.symbol}"
        elif param.is_address:
            value = str(client.get_identity(param.value))
        else:
            value = param.value
        params.append(f'{param.name}="{value}"')
    msg += ",".join(params)
    return msg + ")"


def handler_from(directory):
    import http.server

    class RequestHandler(http.server.SimpleHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            a = list(args)
            a.pop()
            logger.info(" - ".join([str(x) for x in a]))

    def _init(self, *args, **kwargs):
        return RequestHandler.__init__(self, *args, directory=self.directory, **kwargs)

    return type(f'HandlerFrom<{directory}>',
                (RequestHandler,),
                {'__init__': _init, 'directory': directory})


class Cli:

    def __init__(self, chain: str, cache_path: str):
        # Init cache
        self.cache_path = cache_path
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)
        # Init chain client
        self.chain = chain

    def block(self, block: Optional[int]):
        """
        Dumps info around a given block
        :param int block: the block to query, last if not provided
        """
        from humanize import precisedelta
        from datetime import datetime, timedelta
        from json import dumps
        client = get_client(chain_id=self.chain, cache_path=self.cache_path)
        last_block = client.last_block_number
        # Calculate block
        if not block:
            block = last_block
        delta = (last_block - block) * client.block_duration
        at = datetime.now() - timedelta(seconds=delta)
        result = {
            "block": block,
            "block_current": last_block,
            "delta_seconds": int(delta),
            "delta_time": precisedelta(delta),
            "delta_date": str(at)
        }
        print(dumps(result, indent=2))

    # noinspection SpellCheckingInspection
    def event_watch(self, address: str, method: str, min_amount: int, tail: bool, count: int, format: str):
        """
        :param str address: address to look for
        :param str method: method to look for
        :param int min_amount: min amount for transaction
        :param bool tail: keep watching and poll
        :param int count: how many blocks to look back
        """
        from subclient.extrinsics import SubstrateExtrinsicFilter
        from time import sleep
        client = get_client(chain_id=self.chain, cache_path=self.cache_path)
        ex_filter = SubstrateExtrinsicFilter()
        ex_filter.address_pattern = address.strip() if address else None
        ex_filter.min_amount = min_amount if min_amount else 0
        ex_filter.method_pattern = method.strip() if method else None
        start_block = client.last_block_number - count
        while True:
            end_block = client.last_block_number
            for i in range(start_block, end_block):
                # noinspection PyBroadException
                try:
                    extrinsics = client.get_extrinsics(start_block=i, end_block=i)
                    for extrinsic in extrinsics:
                        if ex_filter.match(extrinsic):
                            if format == "json":
                                from json import dumps
                                dumps(extrinsic, indent=2)
                            else:
                                print(chain_extrinsic_to_text(client, extrinsic))
                        else:
                            logger.debug(f"Ex doesnt match filter {extrinsics}")
                except Exception:
                    import traceback
                    traceback.print_exc()
            # Not tailing
            if not tail:
                break
            # Store where we are an loop
            start_block = end_block
            sleep(client.block_duration)
