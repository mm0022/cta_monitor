import json
from enum import Enum

from nexus_data_hub_sdk.share.sdk_base_model import SDKBaseModel


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SDKBaseModel):
            return obj.to_dict()
        elif isinstance(obj, Enum):
            return obj.name
        else:
            return super().default(obj)
