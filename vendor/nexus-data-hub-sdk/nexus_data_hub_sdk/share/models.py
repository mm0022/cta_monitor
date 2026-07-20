import sys
from decimal import Decimal
from typing import Optional, List, Dict

from pandas import DataFrame

from nexus_data_hub_sdk.client.hub_data import Notebook
from nexus_data_hub_sdk.share.enums import DataType, FileType
from nexus_data_hub_sdk.share.sdk_base_model import SDKBaseModel
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.util.sdk_helper import SdkHelper


class FileMeta(SDKBaseModel):
    exchange_type: str
    business_type: str
    data_type: DataType
    symbol: str
    start_time: int
    end_time: int
    file_name: str
    file_type: FileType
    finger_print: str
    confidence: int
    expire_time: int
    url: str
    updated: bool = True

    def to_notebook(self, filetype: str, download_path: str) -> Notebook:
        return Notebook(key=self.business_type,
                        version=self.start_time,
                        url=self.url,
                        fingerprint=self.finger_print,
                        file_type=filetype,
                        file_name=self.file_name,
                        file_path=download_path)


class FileData(FileMeta):
    data: Optional[DataFrame] = None


class ChunkData(SDKBaseModel):
    start_time: int
    end_time: int
    confidence: int = -1
    missing: bool
    data: Optional[DataFrame] = None


class NotebookRequest(SDKBaseModel):
    key: str
    version: int
    fingerprint: str
    delimiter: str
    file_type: str
    fingerprint_algorithm: str
    override_enabled: bool
    expiry_in: Optional[int] = None
    uploaded: bool


class PreSignedResponse(SDKBaseModel):
    url: str
    method: str
    expire_time: str
    file_name: str


class NotebookListRequest(SDKBaseModel):
    key: str
    file_type: str
    lower_bound: Optional[int]
    upper_bound: Optional[int]
    limit: Optional[int]
    sort_direction: str


class NotebookListResponse(SDKBaseModel):
    key: str
    version: int
    fingerprint: str
    file_type: str
    fingerprint_algorithm: str = 'SHA256'
    file_name: str
    url: str

    def to_notebook(self, download_path: Optional[str]) -> Notebook:
        return Notebook(key=self.key,
                        version=self.version,
                        url=self.url,
                        fingerprint=self.fingerprint,
                        file_type=self.file_type,
                        fingerprint_algorithm=self.fingerprint_algorithm,
                        file_name=self.file_name,
                        file_path=download_path)


class ListRequest(SDKBaseModel):
    exchange: str
    business: str
    category: str
    sym: str
    start: int
    end: int

    def get_key(self) -> str:
        return '{}-{}-{}'.format(self.exchange, self.business, self.sym)


class Period(SDKBaseModel):
    start_time: int
    end_time: int


class S3Info(Period):
    url: str
    confidence: int
    file_type: FileType
    file_name: str
    expire_time: int
    finger_print: str


class S3StreamingInfo(Period):
    url: str
    file_type: FileType
    file_name: str
    finger_print: str
    fingerprint_algorithm: str


class HotData(SDKBaseModel):
    start_time: int
    end_time: int
    confidence: int
    data: List[str]


class ListResponse(SDKBaseModel):
    exchange: str
    business: str
    category: DataType
    sym: str
    s3: List[S3Info]
    missing: List[Period]
    data_center: List[Period]
    hot_data: Optional[List[HotData]] = None

    def get_s3(self) -> List[FileMeta]:
        return [FileMeta(exchange_type=self.exchange,
                         business_type=self.business,
                         data_type=self.category,
                         symbol=self.sym,
                         start_time=v.start_time,
                         end_time=v.end_time,
                         file_name=Constants.DATA_FILE_NAME_TEMPLATE.format(
                             self.exchange, self.business, self.category.name,
                             self.sym, v.start_time, v.end_time),
                         file_type=v.file_type,
                         finger_print=v.finger_print,
                         confidence=v.confidence,
                         expire_time=v.expire_time,
                         url=v.url) for v in self.s3]

    def get_missing(self) -> List[ChunkData]:
        return [ChunkData(start_time=v.start_time,
                          end_time=v.end_time,
                          missing=True) for v in self.missing]

    def get_data_center(self) -> List[ChunkData]:
        return [ChunkData(start_time=v.start_time,
                          end_time=v.end_time,
                          missing=False) for v in self.data_center]

    def get_hot_data(self) -> Optional[List[ChunkData]]:
        return None if self.hot_data is None else [ChunkData(start_time=v.start_time,
                                                             end_time=v.end_time,
                                                             missing=False,
                                                             confidenct=v.confidence,
                                                             data=SdkHelper.parse_data(v.data, self.category))
                                                   for v in self.hot_data]


class DataResponse(SDKBaseModel):
    exchange: str
    business: str
    category: DataType
    sym: str
    confidence: int
    data: List[str]
    symbol_id: str


class StreamingAndSequencedDataResponse(SDKBaseModel):
    key: str
    data: List[str]


class StreamingData(SDKBaseModel):
    key: str
    content: str
    seq_number: int
    content_type: str
    package_frequency: str
    start_time: int
    end_time: int


class StreamingAndSequencedListRequest(SDKBaseModel):
    key: str
    start: int
    end: int


class SequencedLatestRequest(SDKBaseModel):
    key: str
    limit: int


class StreamingListResponse(SDKBaseModel):
    key: str
    s3: List[S3StreamingInfo]
    data_center: List[Period]

    def get_s3(self) -> List[FileMeta]:
        return [FileMeta(exchange_type=Constants.EXCHANGE_CYBERX,
                         business_type=self.key,
                         data_type=DataType.STREAMING,
                         symbol=Constants.SYMBOL_ALL,
                         start_time=v.start_time,
                         end_time=v.end_time,
                         file_name=Constants.DATA_FILE_NAME_TEMPLATE.format(
                             Constants.EXCHANGE_CYBERX, self.key, DataType.STREAMING,
                             Constants.SYMBOL_ALL, v.start_time, v.end_time),
                         file_type=v.file_type,
                         finger_print=v.finger_print,
                         confidence=Constants.MAX_CONFIDENCE,
                         expire_time=Constants.MAX_TIMESTAMP,
                         url=v.url) for v in self.s3]

    def get_data_center(self) -> List[ChunkData]:
        return [ChunkData(start_time=v.start_time,
                          end_time=v.end_time,
                          missing=False) for v in self.data_center]


class Range(SDKBaseModel):
    start: int
    end: int


class S3SequencedInfo(Range):
    url: str
    file_type: FileType
    file_name: str
    finger_print: str
    fingerprint_algorithm: str


class SequencedCommitData(SDKBaseModel):
    key: str
    contents: List[str]
    content_type: str
    seq_number: Optional[int] = None
    pre_seq_number: Optional[int] = None


class SequencedData(SDKBaseModel):
    key: str
    content: str
    content_type: str
    seq_number: int


class SequencedListResponse(SDKBaseModel):
    key: str
    s3: List[S3SequencedInfo]
    data_center: List[Range]

    def get_s3(self) -> List[FileMeta]:
        return [FileMeta(exchange_type=Constants.EXCHANGE_CYBERX,
                         business_type=self.key,
                         data_type=DataType.SEQUENCED,
                         symbol=Constants.SYMBOL_ALL,
                         start_time=v.start,
                         end_time=v.end,
                         file_name=Constants.DATA_FILE_NAME_TEMPLATE.format(
                             Constants.EXCHANGE_CYBERX, self.key, DataType.SEQUENCED,
                             Constants.SYMBOL_ALL, v.start, v.end),
                         file_type=v.file_type,
                         finger_print=v.finger_print,
                         confidence=Constants.MAX_CONFIDENCE,
                         expire_time=Constants.MAX_TIMESTAMP,
                         url=v.url) for v in self.s3]

    def get_data_center(self) -> List[ChunkData]:
        return [ChunkData(start_time=v.start,
                          end_time=v.end,
                          missing=False) for v in self.data_center]


class SequencedLatestResponse(SDKBaseModel):
    key: str
    s3: List[S3SequencedInfo]
    data: List[str]

    def get_s3(self) -> List[FileMeta]:
        return [FileMeta(exchange_type=Constants.EXCHANGE_CYBERX,
                         business_type=self.key,
                         data_type=DataType.SEQUENCED,
                         symbol=Constants.SYMBOL_ALL,
                         start_time=v.start,
                         end_time=v.end,
                         file_name=Constants.DATA_FILE_NAME_TEMPLATE.format(
                             Constants.EXCHANGE_CYBERX, self.key, DataType.SEQUENCED,
                             Constants.SYMBOL_ALL, v.start, v.end),
                         file_type=v.file_type,
                         finger_print=v.finger_print,
                         confidence=Constants.MAX_CONFIDENCE,
                         expire_time=Constants.MAX_TIMESTAMP,
                         url=v.url) for v in self.s3]

    def get_data(self) -> List[str]:
        return self.data


class SequencedDataRequest(SDKBaseModel):
    key: str
    lower: int
    upper: int
    direction: str = 'ASC'


class CacheResponse(SDKBaseModel):
    key: str
    value: Optional[str]


class CacheSetRequest(CacheResponse):
    ttl: Optional[int]


class PageRequest(SDKBaseModel):
    curPage: int
    pageSize: int


class KlineDetailRequest(PageRequest):
    exchange: Optional[str] = None
    business: Optional[str] = None
    category: Optional[str] = None
    sym: Optional[str] = None

    def get_key(self) -> str:
        key = ''
        if self.exchange is not None:
            key += self.exchange
            if self.business is not None:
                key = key + '-' + self.business
                if self.sym is not None:
                    key = key + '-' + self.sym
        return key


class DetailByKeyRequest(PageRequest):
    key: Optional[str] = None


class ChunkDetail(SDKBaseModel):
    start: int
    end: int
    missing: bool
    confidence: int


class KlineDetail(SDKBaseModel):
    exchange: str
    business: str
    category: str
    sym: str
    start: int
    end: int
    chunks: List[ChunkDetail]


class StreamingAndSequencedBaseDetail(SDKBaseModel):
    key: str
    packagePosition: int
    start: int
    end: int


class StreamingAndSequencedDetail(StreamingAndSequencedBaseDetail):
    frequency: str
    createdAt: int
    updatedAt: int


class NotebookDetail(SDKBaseModel):
    key: str
    fileType: str
    minVersion: int
    maxVersion: int
    count: int


class PageResponseBase(SDKBaseModel):
    totalCount: int
    totalPage: int
    curPage: int
    pageSize: int


class KlinePageData(PageResponseBase):
    resources: List[KlineDetail]


class StreamingAndSequencedPageData(PageResponseBase):
    resources: List[StreamingAndSequencedDetail]


class NotebookPageData(PageResponseBase):
    resources: List[NotebookDetail]


class KeyAndLimitRequest(SDKBaseModel):
    key: Optional[str] = None
    start: Optional[str] = None
    included: Optional[bool] = None
    limit: Optional[int] = None


class KeysRequest(SDKBaseModel):
    keys: List[str]


class RouteMetaResponse(SDKBaseModel):
    checksum: Optional[str]
    defaults: Optional[str]
    destinations: Dict[str, str]


class MetaSymbol(SDKBaseModel):
    id: Optional[int]
    sym: Optional[str]
    code: Optional[str]
    alias: Optional[str]
    exchange: Optional[str]
    providerName: Optional[str]
    type: Optional[str]
    base: Optional[str]
    counter: Optional[str]
    originalBase: Optional[str]
    originalCounter: Optional[str]
    originalSymbol: Optional[str]
    baseDecimal: Optional[int]
    counterDecimal: Optional[int]
    minPrice: Optional[Decimal]
    maxPrice: Optional[Decimal]
    minPricePercent: Optional[str]
    maxPricePercent: Optional[str]
    tickSize: Optional[Decimal]
    minQty: Optional[Decimal]
    maxQty: Optional[Decimal]
    icebergAllowed: Optional[bool]
    symbolId: Optional[str]
    lotSize: Optional[Decimal]
    minNotional: Optional[Decimal]
    marginMode: Optional[int]
    leverageRatio: Optional[Decimal]
    crossLeverageRatio: Optional[Decimal]
    contractType: Optional[str]
    inverse: Optional[bool]
    deliveryDate: Optional[str]
    deliveryTime: Optional[int]
    settlementTime: Optional[int]
    settlementType: Optional[str]
    contractMultiple: Optional[Decimal]
    underlyingAsset: Optional[str]
    underlyingAssetId: Optional[int]
    positionCurrency: Optional[str]
    marginCurrency: Optional[str]
    optionType: Optional[str]
    strike: Optional[Decimal]
    listed: Optional[bool]
    tradeTtl: Optional[int]
    orderbookTtl: Optional[int]
    crc32: Optional[int]
