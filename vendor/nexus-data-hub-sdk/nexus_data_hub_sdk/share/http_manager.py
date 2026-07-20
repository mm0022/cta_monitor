import ast
import json
import os.path
import uuid
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from httpx import Response

from nexus_data_hub_sdk.exception.exceptions import NexusHubAPIError, FileOperationError
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.share.models import (NotebookRequest, PreSignedResponse, NotebookListRequest,
                                             NotebookListResponse, ListRequest, ListResponse, DataResponse,
                                             StreamingData, StreamingAndSequencedListRequest, StreamingListResponse,
                                             StreamingAndSequencedDataResponse, CacheSetRequest, CacheResponse,
                                             SequencedListResponse, SequencedCommitData, SequencedDataRequest,
                                             SequencedData, KlinePageData, StreamingAndSequencedPageData,
                                             NotebookPageData, KlineDetailRequest, DetailByKeyRequest,
                                             KeyAndLimitRequest, KeysRequest, StreamingAndSequencedBaseDetail,
                                             RouteMetaResponse, SequencedLatestRequest, SequencedLatestResponse,
                                             MetaSymbol)
from nexus_data_hub_sdk.share.decorator import exception_wrapper, retry
from nexus_data_hub_sdk.share.logger import logger


class HttpManager:
    def __init__(self, api_key: str, gateway_url: str, route_meta_uri: str, timeout: float = 5.0):
        self.__api_key = api_key
        self.__gateway_url = gateway_url
        self.__route_meta_uri = route_meta_uri
        transport = httpx.HTTPTransport(retries=5, http2=True)
        self.__manager = httpx.Client(transport=transport, timeout=timeout)
        self.__route_meta = None

    def __refresh_route_meta(self, old_checksum: Optional[str]):
        try:
            with self.__manager.stream('GET', self.__route_meta_uri) as response:
                if response.status_code == 200:
                    response.read()
                    s3_route_meta = self.__build_route_meta(response.json())
                    if old_checksum is None or old_checksum != s3_route_meta.checksum:
                        self.__route_meta = s3_route_meta
                        return
        except Exception:
            # failed to get route meta from s3, do nothing here, than get route meta from gateway
            pass

        try:
            resp = self.__manager.request('GET',
                                          urljoin(self.__gateway_url, Constants.ROUTE_META_API_PATH_URL))
        except Exception as e:
            raise NexusHubAPIError(
                "Data hub gateway unreachable. {}".format(e))
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            route_dict = json.loads(data)
            gateway_route_meta = self.__build_route_meta(route_dict)
            self.__route_meta = gateway_route_meta
        else:
            raise NexusHubAPIError(
                'Failed to retrieve route data. {}'.format(data))

    @staticmethod
    def __build_route_meta(route_dict) -> RouteMetaResponse:
        route_meta = RouteMetaResponse.from_dict(route_dict)
        if route_meta.checksum is None:
            raise NexusHubAPIError('Gateway route table has no record')
        route_meta.destinations = {k.upper(): v if v.endswith('/') else v + '/'
                                   for k, v in route_meta.destinations.items()}
        route_meta.defaults = route_meta.defaults.upper()
        return route_meta

    def __del__(self):
        try:
            self.__manager.close()
        except Exception as e:
            # Ignore any errors during cleanup as this is called during garbage collection
            logger.debug(f"Error during HttpManager cleanup: {str(e)}")

    @staticmethod
    @exception_wrapper(exception=NexusHubAPIError)
    def __validate_url(data_hub_url: str) -> str:
        urlparse(data_hub_url)
        return data_hub_url

    def __get_url_base(self, keys: List[str]) -> str:
        result = set()
        for key in keys:
            matched = False
            for prefix in self.__route_meta.destinations.keys():
                if key.upper().startswith(prefix):
                    result.add(self.__route_meta.destinations[prefix])
                    matched = True
                    break
            if not matched:
                srv = self.__route_meta.destinations.get(
                    self.__route_meta.defaults)
                if srv is not None:
                    result.add(srv)
                else:
                    raise NexusHubAPIError(
                        'Failed to get default data hub route')
                logger.warning('Default route is used')
        if len(result) == 1:
            return self.__validate_url(list(result)[0])
        raise NexusHubAPIError('Multiply data hub route in one method')

    def get(self, url: str, fields: Dict, route_meta_checksum: str, request_id: str = str(uuid.uuid4())) -> Response:
        return self.__manager.request('GET', url, params=fields,
                                      headers={Constants.CHECKSUM_HEADER_NAME: route_meta_checksum,
                                               Constants.API_KEY_HEADER_NAME: self.__api_key,
                                               Constants.SDK_VERSION_HEADER_NAME: Constants.SDK_VERSION,
                                               Constants.SDK_REQUEST_ID: request_id})

    def post(self, url: str, body: str, route_meta_checksum: str, request_id: str = str(uuid.uuid4())) -> Response:
        return self.__manager.request('POST', url, content=body.encode('utf-8'),
                                      headers={'Content-Type': 'application/json',
                                               Constants.CHECKSUM_HEADER_NAME: route_meta_checksum,
                                               Constants.API_KEY_HEADER_NAME: self.__api_key,
                                               Constants.SDK_VERSION_HEADER_NAME: Constants.SDK_VERSION,
                                               Constants.SDK_REQUEST_ID: request_id})

    def put(self, url: str, data: bytes, headers: Dict) -> Response:
        headers[Constants.SDK_VERSION_HEADER_NAME] = Constants.SDK_VERSION
        return self.__manager.request('PUT', url, content=data, headers=headers)

    def __get_with_route(self, keys: List[str], url: str, fields: Dict) -> Response:
        if self.__route_meta is None:
            self.__refresh_route_meta(None)
        request_id = str(uuid.uuid4())
        route_meta_checksum = self.__route_meta.checksum
        try:
            resp = self.get(urljoin(self.__get_url_base(keys), url),
                            fields,
                            route_meta_checksum,
                            request_id=request_id)
            if resp.status_code == 412:
                content = ast.literal_eval(resp.content.decode('utf-8'))
                if Constants.INVALID_ROUTE_ERROR_MESSAGE in content['details']:
                    self.__refresh_route_meta(route_meta_checksum)
                    route_meta_checksum = self.__route_meta.checksum
                    return self.get(urljoin(self.__get_url_base(keys), url),
                                    fields,
                                    route_meta_checksum,
                                    request_id=request_id)
            return resp
        except Exception as e:
            raise type(e)('[Get request[{}] for {}: {}, with args: {}]'.format(
                request_id, url, e, fields)) from e

    def __post_with_route(self, keys: List[str], url: str, body: str) -> Response:
        if self.__route_meta is None:
            self.__refresh_route_meta(None)
        request_id = str(uuid.uuid4())
        route_meta_checksum = self.__route_meta.checksum
        try:
            resp = self.post(urljoin(self.__get_url_base(keys), url),
                             body,
                             route_meta_checksum,
                             request_id=request_id)
            if resp.status_code == 412:
                self.__refresh_route_meta(route_meta_checksum)
                route_meta_checksum = self.__route_meta.checksum
                return self.post(urljoin(self.__get_url_base(keys), url),
                                 body,
                                 route_meta_checksum,
                                 request_id=request_id)
            else:
                return resp
        except Exception as e:
            raise type(e)('[Post request[{}] for {}: {}, with args: {}]'.format(
                request_id, url, e, body)) from e

    @exception_wrapper(exception=NexusHubAPIError)
    def notebook_pre_signed(self, note_book_request: NotebookRequest) -> PreSignedResponse:
        resp = self.__post_with_route([note_book_request.key], Constants.NOTEBOOK_PRE_SIGNED_API_PATH_URL,
                                      note_book_request.to_json())
        data = resp.content.decode('utf-8')
        if resp.status_code == 201:
            return PreSignedResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def notebook_commit(self, note_book_request: NotebookRequest) -> Optional[NotebookListResponse]:
        resp = self.__post_with_route([note_book_request.key], Constants.NOTEBOOK_COMMIT_API_PATH_URL,
                                      note_book_request.to_json())
        data = resp.content.decode('utf-8')
        if resp.status_code == 201:
            if len(data) == 0:
                return None
            else:
                return NotebookListResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=FileOperationError)
    def http_upload(self, file_path: str, fingerprint: str, url: str):
        with open(file_path, 'rb') as f:
            headers = {
                'x-amz-checksum-sha256': fingerprint,
                'content-length': str(os.path.getsize(file_path))
            }
            resp = self.put(url, f.read(), headers)
        if resp.status_code != 200:
            logger.error('Failed to upload file to {}'.format(
                urljoin(url, urlparse(url).path)))
            raise Exception(resp.content.decode('utf-8'))

    @exception_wrapper(exception=FileOperationError)
    def http_upload_binary(self, data: bytes, fingerprint: str, url: str):
        headers = {
            'x-amz-checksum-sha256': fingerprint,
            'content-length': str(len(data))
        }
        resp = self.put(url, data, headers)
        if resp.status_code != 200:
            logger.error('Failed to upload binary data to {}'.format(
                urljoin(url, urlparse(url).path)))
            raise Exception(resp.content.decode('utf-8'))

    @exception_wrapper(exception=NexusHubAPIError)
    @retry(max_retries=3, delay=1.0, backoff=2.0)
    def notebook_list(self, note_book_list_request: NotebookListRequest) -> List[NotebookListResponse]:
        resp = self.__get_with_route([note_book_list_request.key], Constants.NOTEBOOK_LIST_API_PATH_URL,
                                     note_book_list_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return [NotebookListResponse.from_dict(d) for d in json.loads(data)]
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def list(self, list_request: ListRequest) -> ListResponse:
        resp = self.__get_with_route(
            [list_request.get_key()], Constants.LIST_API_PATH_URL, list_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return ListResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def data(self, data_request: ListRequest) -> DataResponse:
        resp = self.__get_with_route(
            [data_request.get_key()], Constants.DATA_API_PATH_URL, data_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return DataResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_commit(self, streaming_data: StreamingData):
        resp = self.__post_with_route([streaming_data.key],
                                      Constants.STREAMING_COMMIT_API_PATH_URL,
                                      streaming_data.to_json())
        if resp.status_code != 201:
            raise Exception(resp.content.decode('utf-8'))

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_list(self, list_request: StreamingAndSequencedListRequest) -> StreamingListResponse:
        resp = self.__get_with_route([list_request.key],
                                     Constants.STREAMING_LIST_API_PATH_URL,
                                     list_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return StreamingListResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_data(self, data_request: StreamingAndSequencedListRequest) -> StreamingAndSequencedDataResponse:
        resp = self.__get_with_route([data_request.key],
                                     Constants.STREAMING_DATA_API_PATH_URL,
                                     data_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return StreamingAndSequencedDataResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def cache_set(self, cache_set_request: CacheSetRequest) -> CacheResponse:
        resp = self.__post_with_route([cache_set_request.key],
                                      Constants.CACHE_SET_API_PATH_URL,
                                      cache_set_request.to_json())
        data = resp.content.decode('utf-8')
        if resp.status_code == 201:
            return CacheResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def cache_get(self, cache_get_key: str) -> CacheResponse:
        resp = self.__get_with_route([cache_get_key],
                                     Constants.CACHE_GET_API_PATH_URL,
                                     {'key': cache_get_key})
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return CacheResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_commit(self, sequenced_streaming_data: SequencedCommitData) -> List[SequencedData]:
        resp = self.__post_with_route([sequenced_streaming_data.key],
                                      Constants.SEQUENCED_COMMIT_API_PATH_URL,
                                      sequenced_streaming_data.to_json())
        data = resp.content.decode('utf-8')
        if resp.status_code == 201:
            return [SequencedData.from_dict(item) for item in json.loads(data)]
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_list(self, list_request: StreamingAndSequencedListRequest) -> SequencedListResponse:
        resp = self.__get_with_route([list_request.key],
                                     Constants.SEQUENCED_LIST_API_PATH_URL,
                                     list_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return SequencedListResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_data(self, data_request: SequencedDataRequest) -> StreamingAndSequencedDataResponse:
        resp = self.__get_with_route([data_request.key],
                                     Constants.SEQUENCED_DATA_API_PATH_URL,
                                     data_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return StreamingAndSequencedDataResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_latest(self, sequenced_latest_request: SequencedLatestRequest) -> SequencedLatestResponse:
        resp = self.__get_with_route([sequenced_latest_request.key],
                                     Constants.SEQUENCED_LATEST_API_PATH_URL,
                                     sequenced_latest_request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return SequencedLatestResponse.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def kline_detail(self, request: KlineDetailRequest) -> KlinePageData:
        resp = self.__get_with_route(
            [request.get_key()], Constants.KLINE_DETAIL_API_PATH_URL, request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return KlinePageData.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_detail(self, request: DetailByKeyRequest) -> StreamingAndSequencedPageData:
        resp = self.__get_with_route([request.key if request.key is not None else ''],
                                     Constants.STREAMING_DETAIL_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return StreamingAndSequencedPageData.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_detail(self, request: DetailByKeyRequest) -> StreamingAndSequencedPageData:
        resp = self.__get_with_route([request.key if request.key is not None else ''],
                                     Constants.SEQUENCED_DETAIL_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return StreamingAndSequencedPageData.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def notebook_detail(self, request: DetailByKeyRequest) -> NotebookPageData:
        resp = self.__get_with_route([request.key if request.key is not None else ''],
                                     Constants.NOTEBOOK_DETAIL_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return NotebookPageData.from_dict(json.loads(data))
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_limited_keys(self, request: KeyAndLimitRequest) -> List[str]:
        resp = self.__get_with_route([request.key if request.key is not None else ''],
                                     Constants.STREAMING_LIMITED_KEYS_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return json.loads(data)
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_limited_keys(self, request: KeyAndLimitRequest) -> List[str]:
        resp = self.__get_with_route([request.key if request.key is not None else ''],
                                     Constants.SEQUENCED_LIMITED_KEYS_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return json.loads(data)
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def streaming_limited_details(self, request: KeysRequest) -> List[StreamingAndSequencedBaseDetail]:
        resp = self.__get_with_route(request.keys,
                                     Constants.STREAMING_LIMITED_DETAILS_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            ret = list()
            for item in json.loads(data):
                ret.append(StreamingAndSequencedBaseDetail.from_dict(item))
            return ret
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def sequenced_limited_details(self, request: KeysRequest) -> List[StreamingAndSequencedBaseDetail]:
        resp = self.__get_with_route(request.keys,
                                     Constants.SEQUENCED_LIMITED_DETAILS_API_PATH_URL,
                                     request.to_dict())
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            ret = list()
            for item in json.loads(data):
                ret.append(StreamingAndSequencedBaseDetail.from_dict(item))
            return ret
        raise Exception(data)

    @exception_wrapper(exception=NexusHubAPIError)
    def get_meta_symbols(self, request: List[str]) -> List[MetaSymbol]:
        resp = self.__get_with_route([''],
                                     Constants.META_SYMBOL_API_PATH_URL,
                                     {'symbols': request})
        data = resp.content.decode('utf-8')
        if resp.status_code == 200:
            return [MetaSymbol.from_dict(item) for item in json.loads(data)]
        raise Exception(data)
