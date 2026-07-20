from typing import Optional

from pandas import DataFrame

from nexus_data_hub_sdk.share.sdk_base_model import SDKBaseModel


class HubData(SDKBaseModel):
    missing: bool = False
    updated: bool = False
    data: DataFrame


class Notebook(SDKBaseModel):
    key: str
    version: int
    url: str
    fingerprint: str
    file_type: str
    fingerprint_algorithm: str = 'SHA256'
    file_name: str
    file_path: Optional[str]
