from subclient.core import SubstrateClient, SubstrateEndpoint, T
from subclient.moonbeam import MoonbeamClient
from typing import List, Type
import logging

# WSS Endpoints
endpoints = [
    SubstrateEndpoint[MoonbeamClient](
        chain_id="moonbase",
        wss_endpoints=[
            "wss.api.moonbase.moonbeam.network",
            "moonbeam-alpha.api.onfinality.io/public-ws"
        ],
        client_type=MoonbeamClient,
        options={
            "rpc_endpoints": [
                "https://rpc.api.moonbase.moonbeam.network"
            ]
        }
    ),
    SubstrateEndpoint[MoonbeamClient](
        chain_id="moonbeam",
        wss_endpoints=[
            "wss.api.moonbeam.network",
            "moonbeam.api.onfinality.io/public-ws"
        ],
        client_type=MoonbeamClient,
        options={
            "rpc_endpoints": [
                "https://rpc.api.moonbeam.network"
            ]
        }
    ),
    SubstrateEndpoint[MoonbeamClient](
        chain_id="moonriver",
        wss_endpoints=[
            "wss.moonriver.moonbeam.network",
            "moonbeam-rpc.dwellir.com",
            "moonriver.api.onfinality.io/public-ws"
        ],
        client_type=MoonbeamClient,
        options={
            "rpc_endpoints": [
                "https://rpc.api.moonriver.moonbeam.network"
            ]
        }
    ),
]


def get_endpoint_ids() -> List[str]:
    return [x.chain_id for x in endpoints]


def get_endpoint(chain_id: str) -> SubstrateEndpoint:
    for endpoint in endpoints:
        if endpoint.chain_id == chain_id:
            return endpoint
    raise NameError(f"Endpoint with ID {chain_id} not supported")


# noinspection PyUnusedLocal
def get_client(chain_id: str, cache_path: str, wss_endpoint: str = None, t: Type[T] = SubstrateClient) -> T:
    """
    Will create a chain client
    :param str chain_id: the chain name, es: "polkadot", "kusama", "moonbeam"
    :param str cache_path: the cache path for the client
    :param str wss_endpoint: override wss uri client will connect to
    :param Type[T] t: force client type casting to T for type hints
    """
    endpoint = get_endpoint(chain_id)
    if wss_endpoint:
        endpoint.wss_endpoints = [wss_endpoint]
    client = endpoint.get_client(cache_path=cache_path)
    return client


def setup_logging(app_name, level):
    import coloredlogs
    coloredlogs.install(level=logging.INFO, logger=logging.getLogger())
    coloredlogs.adjust_level(level=logging.WARNING, logger=logging.getLogger('substrateinterface'))
    coloredlogs.adjust_level(level=level, logger=logging.getLogger(app_name))
    coloredlogs.adjust_level(level=level, logger=logging.getLogger('subclient'))
