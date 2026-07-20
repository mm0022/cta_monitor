import importlib.metadata
import os
from pathlib import Path
from typing import Final

import tomli
from pydantic.version import VERSION as PYDANTIC_VERSION

from nexus_data_hub_sdk.share.settings import ROUTE_META_BUCKET, ROUTE_META_KEY


class Constants:
    @staticmethod
    def get_sdk_version() -> str:
        path = os.path.join(Path(__file__).resolve(
        ).parent.parent.parent, 'pyproject.toml')
        if os.path.exists(path):
            with open(path) as f:
                meta = tomli.loads(f.read())
                return str(meta.get('tool', {}).get('poetry', {}).get('version', 'undefined'))
        else:
            return importlib.metadata.version('nexus-data-hub-sdk')

    CACHE_DIRECTORY: Final = './.data'
    MEAT_FILE_NAME: Final = 'meta.dat'
    MAX_THREAD: Final = os.cpu_count()
    DATA_HUB_BASE_URL: Final = 'data-api/v1'
    LIST_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/list'
    DATA_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/data'
    NOTEBOOK_PRE_SIGNED_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/notebook/pre-signed'
    NOTEBOOK_COMMIT_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/notebook/commit'
    NOTEBOOK_LIST_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/notebook/list'
    STREAMING_COMMIT_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/lake/commit'
    STREAMING_LIST_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/event-bus/list'
    STREAMING_DATA_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/event-bus/data/time-range'
    SEQUENCED_COMMIT_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/sequenced/commit'
    SEQUENCED_LIST_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/sequenced/list'
    SEQUENCED_DATA_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/sequenced/data'
    SEQUENCED_LATEST_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/sequenced/latest'
    CACHE_SET_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/cache/set'
    CACHE_GET_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/cache/get'
    KLINE_DETAIL_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/data-detail/klines'
    STREAMING_DETAIL_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/data-detail/lakes'
    SEQUENCED_DETAIL_API_PATH_URL: Final = DATA_HUB_BASE_URL + \
        '/data-detail/sequencedlakes'
    NOTEBOOK_DETAIL_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/data-detail/notebooks'
    STREAMING_LIMITED_KEYS_API_PATH_URL: Final = DATA_HUB_BASE_URL + \
        '/data-detail/lakes/limited-keys'
    STREAMING_LIMITED_DETAILS_API_PATH_URL: Final = DATA_HUB_BASE_URL + \
        '/data-detail/lakes/limited-details'
    SEQUENCED_LIMITED_KEYS_API_PATH_URL: Final = DATA_HUB_BASE_URL + \
        '/data-detail/sequencedlakes/limited-keys'
    SEQUENCED_LIMITED_DETAILS_API_PATH_URL: Final = DATA_HUB_BASE_URL + \
        '/data-detail/sequencedlakes/limited-details'
    META_SYMBOL_API_PATH_URL: Final = DATA_HUB_BASE_URL + '/symbols'
    ROUTE_META_API_PATH_URL: Final = 'data-api/v1/route-meta'
    DATA_FILE_NAME_TEMPLATE: Final = '{}-{}-{}-{}-{}_{}'
    MAX_TIMESTAMP: Final = 9999999999999
    MAX_INTEGER: Final = 9223372036854775807
    MAX_CONFIDENCE: Final = 6
    PYDANTIC_VERSION: Final = PYDANTIC_VERSION
    DATA_HUB_URL_ROOT_STAGING_IN_CLUSTER: Final = 'http://nexus-data-hub.pacifica:8080'
    DATA_HUB_URL_ROOT_PROD_IN_CLUSTER: Final = 'http://nexus-data-hub.pacifica:8080'
    DATA_HUB_URL_ROOT_STAGING_IN_LOCAL: Final = 'https://nexus.cyberx.cc/'
    DATA_HUB_URL_ROOT_PROD_IN_LOCAL: Final = 'https://nexus.cyberx.com/'
    CHECKSUM_SHA256: Final = 'SHA256'
    FILE_CHUNK_SIZE: Final = 1048576
    ONE_SECOND_IN_MILLI: Final = 1000
    EXCHANGE_CYBERX: Final = 'CYBERX'
    SYMBOL_ALL: Final = 'ALL'
    PAGE_SIZE: Final = 200
    CHECKSUM_HEADER_NAME: Final = 'X-Route-Meta-Checksum'
    API_KEY_HEADER_NAME: Final = 'X-Data-Hub-Api-Key'
    SDK_VERSION_HEADER_NAME: Final = 'X-Data-Hub-Sdk-Version'
    SDK_REQUEST_ID: Final = 'X-Data-Hub-Sdk-Request-Id'
    SDK_VERSION: Final = get_sdk_version()
    INVALID_ROUTE_ERROR_MESSAGE = 'Invalid route meta info'
    ROUTE_META_S3_URI: Final = 'https://{}.s3.amazonaws.com/{}'.format(
        ROUTE_META_BUCKET, ROUTE_META_KEY)
