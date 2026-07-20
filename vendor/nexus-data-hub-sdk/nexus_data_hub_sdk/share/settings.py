import decimal
import os
from typing import Type, Final

from numpy import float64

from nexus_data_hub_sdk.exception.exceptions import SetupError


def get_decimal_storage_type_from_environment() -> Type:
    storage_type = os.environ.get('DECIMAL_STORAGE_TYPE', default='FLOAT')
    if storage_type == 'FLOAT':
        return float64
    elif storage_type == 'STRING':
        return str
    elif storage_type == 'DECIMAL':
        return decimal.Decimal
    else:
        raise SetupError('Decimal storage type invalid')


def get_gateway_url_from_environment() -> str:
    url = os.environ.get('DATA_HUB_GATEWAY_URL',
                         default='https://nexus.tyo.cyberx.com/nexus-data-hub-gateway/')
    return url if url.endswith('/') else url + '/'


DECIMAL_STORAGE_TYPE: Final = get_decimal_storage_type_from_environment()
LOGGING_LEVEL: Final = os.environ.get('SDK_LOGGING_LEVEL', default='INFO')
DATA_HUB_GATEWAY_URL: Final = get_gateway_url_from_environment()

ROUTE_META_BUCKET: Final = os.environ.get(
    'ROUTE_META_BUCKET', default='nexus-data-hub-prime-cta-tky')
ROUTE_META_KEY: Final = os.environ.get(
    'ROUTE_META_KEY', default='meta/route_meta.json')
