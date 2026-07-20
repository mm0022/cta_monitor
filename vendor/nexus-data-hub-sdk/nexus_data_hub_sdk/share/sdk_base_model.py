from typing import Dict, TypeVar, Type

from pydantic import BaseModel, ConfigDict

from nexus_data_hub_sdk.share.constants import Constants


T = TypeVar('T', bound='SdkBaseModel')


class SDKBaseModel(BaseModel):
    if Constants.PYDANTIC_VERSION.startswith('1'):
        def to_dict(self) -> Dict:
            return self.dict(exclude_none=True)

        def to_json(self) -> str:
            return self.json(exclude_none=True)

        @classmethod
        def from_dict(cls: Type[T], values: Dict) -> T:
            return cls(**values)

        class Config:
            arbitrary_types_allowed = True
    else:
        model_config = ConfigDict(arbitrary_types_allowed=True)

        def to_dict(self) -> Dict:
            return self.model_dump(exclude_none=True)

        def to_json(self) -> str:
            return self.model_dump_json(exclude_none=True)

        @classmethod
        def from_dict(cls: Type[T], values: Dict) -> T:
            return cls.model_validate(values)
