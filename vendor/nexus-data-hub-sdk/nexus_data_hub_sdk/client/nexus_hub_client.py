from __future__ import annotations

import os
from copy import deepcopy
from io import StringIO
from typing import List, Dict, Tuple, Optional, Generator

import numpy as np
import pandas as pd
from pandas import DataFrame

from nexus_data_hub_sdk.exception.exceptions import SDKError
from nexus_data_hub_sdk.downloader.download_adapter import DownloadAdapter
from nexus_data_hub_sdk.downloader.http_download_adapter import HttpDownloadAdapter
from nexus_data_hub_sdk.aggregator.data_validator import DataValidator
from nexus_data_hub_sdk.aggregator.aggregator import DataAggregator
from nexus_data_hub_sdk.cache.cache_manager import CacheManager
from nexus_data_hub_sdk.client.config import Config
from nexus_data_hub_sdk.client.hub_data import HubData, Notebook
from nexus_data_hub_sdk.downloader.s3_download_adapter import S3DownloadAdapter
from nexus_data_hub_sdk.downloader.downloader import Downloader, DownloadTask
from nexus_data_hub_sdk.exception.exceptions import ParamInvalidError, NexusHubAPIError, FileOperationError, DataError
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.share.decorator import exception_wrapper
from nexus_data_hub_sdk.share.enums import DataType, FileType
from nexus_data_hub_sdk.share.executor import Executor
from nexus_data_hub_sdk.share.http_manager import HttpManager
from nexus_data_hub_sdk.share.models import (FileData, FileMeta, ChunkData, NotebookRequest, NotebookListRequest,
                                             ListRequest, StreamingData, StreamingAndSequencedListRequest,
                                             CacheSetRequest, CacheResponse, SequencedDataRequest, SequencedCommitData,
                                             SequencedData, KlineDetailRequest, DetailByKeyRequest, KlineDetail,
                                             PageResponseBase, StreamingAndSequencedDetail, NotebookDetail,
                                             StreamingAndSequencedBaseDetail, KeyAndLimitRequest, KeysRequest,
                                             SequencedLatestRequest, MetaSymbol)
from nexus_data_hub_sdk.util.file_helper import FileHelper
from nexus_data_hub_sdk.util.date_time_helper import DateTimeHelper
from nexus_data_hub_sdk.share.settings import DATA_HUB_GATEWAY_URL, DECIMAL_STORAGE_TYPE
from nexus_data_hub_sdk.util.sdk_helper import SdkHelper


# Earliest hour for which DataBento EVENT_1H coverage is guaranteed.
# 2022-01-02T23:00:00Z — fetches widened by the 7-day forward-fill lookback
# are floored at this value so we don't request pre-coverage events.
DATABENTO_MIN_EVENT_START_MS = 1641164400000


class Client:
    def __init__(self,
                 api_key: str,
                 directory: str = Constants.CACHE_DIRECTORY,
                 missing_exception: bool = True,
                 updated_exception: bool = True,
                 http_download: bool = True,
                 download_concurrency: int = Constants.MAX_THREAD,
                 api_timeout: float = 30.0,
                 gateway_url: str = DATA_HUB_GATEWAY_URL,
                 route_meta_uri: str = Constants.ROUTE_META_S3_URI,
                 local_first: bool = False):
        """
        Return an instance of the Client class.

        :param api_key: The API key for the operations.
        :param directory: The local file storage directory, default is './.data'.
        :param missing_exception: Indicate if raise exception when data is missing, default is True.
        :param updated_exception: Indicate if raise exception when any file fails to download, default is True.
        :param http_download: Indicate use the http download adapter or not, default is True.
        :param download_concurrency: How many thread to download files, default is the number of CPUs.
        :param api_timeout: The timeout for http requests, default is 30 seconds.
        :param gateway_url: The url of the data hub gateway, default will be set from env.
        :param route_meta_uri: The uri of the route meta file on S3, default will be set from env.
        :param local_first: Request data from local cache first.
        :return: A Client instance.
        :raises ParamInvalidError: If parameter is invalid.
        """
        self.__type_validator('api_key', api_key, str)
        self.__type_validator('directory', directory, str)
        self.__type_validator('missing_exception', missing_exception, bool)
        self.__type_validator('updated_exception', updated_exception, bool)
        self.__type_validator('http_download', http_download, bool)
        self.__type_validator('download_concurrency',
                              download_concurrency, int)
        self.__type_validator('api_timeout', api_timeout, float)
        self.__type_validator('gateway_url', gateway_url, str)
        self.__type_validator('route_meta_uri', route_meta_uri, str)
        self.__type_validator('local_first', local_first, bool)
        self.__config = Config(
            missing_exception, updated_exception, http_download, download_concurrency, api_timeout, local_first)
        self.__local_root_path = directory
        self.__download_adapter = self.__create_download_adapter()
        self.__http_manager = HttpManager(api_key,
                                          gateway_url if gateway_url.endswith(
                                              '/') else gateway_url + '/',
                                          route_meta_uri,
                                          self.__config.api_timeout)

    def __request_file_list(self,
                            symbol: str,
                            business_type: str,
                            start_time: int,
                            end_time: int,
                            data_type: DataType,
                            exchange_type: str,
                            local_only: bool,
                            cache_manager: CacheManager) -> (List[FileMeta], List[ChunkData], List[ChunkData], bool):
        list_request = ListRequest(exchange=exchange_type,
                                   business=business_type,
                                   category=data_type.name,
                                   sym=symbol,
                                   start=start_time,
                                   end=end_time)

        if local_only:
            return self.__generate_local_data_list(
                symbol, business_type, start_time, end_time, data_type, exchange_type, cache_manager)
        list_response = self.__http_manager.list(list_request)
        s3_list = list_response.get_s3()
        center_list = list_response.get_data_center()
        missing_list = list_response.get_missing()
        center_data = list_response.get_hot_data()
        center_data_loaded = center_data is not None
        return s3_list, center_data if center_data_loaded else center_list, missing_list, center_data_loaded

    def __request_streaming_file_list(self,
                                      key: str,
                                      start_time: int,
                                      end_time: int) -> (List[FileMeta], List[ChunkData]):
        list_response = self.__http_manager.streaming_list(StreamingAndSequencedListRequest(key=key,
                                                                                            start=start_time,
                                                                                            end=end_time))
        return list_response.get_s3(), list_response.get_data_center()

    def __request_sequenced_streaming_file_list(self,
                                                key: str,
                                                start_seq_number: int,
                                                end_seq_number: int) -> (List[FileMeta], List[ChunkData]):
        list_response = self.__http_manager.sequenced_list(StreamingAndSequencedListRequest(key=key,
                                                                                            start=start_seq_number,
                                                                                            end=end_seq_number))
        return list_response.get_s3(), list_response.get_data_center()

    def __request_sequenced_streaming_latest(self,
                                             key: str,
                                             limit: int) -> (List[FileMeta], List[str]):
        list_response = self.__http_manager.sequenced_latest(SequencedLatestRequest(key=key,
                                                                                    limit=limit))
        return list_response.get_s3(), list_response.get_data()

    @staticmethod
    def __update_meta(tasks: List[DownloadTask], metas: List[FileMeta]):
        meta_map = {m.file_name: m for m in metas}
        for t in tasks:
            meta = meta_map[t.file_name]
            if t.downloaded:
                meta.updated = True
            else:
                meta.updated = False

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def __read_from_files(s3_meta_list: List[FileMeta], cache_manager: CacheManager) -> List[FileData]:
        data_list = [(FileData(**f.to_dict()), cache_manager)
                     for f in s3_meta_list]
        Executor.submit(Client.__read_from_file, data_list)
        return [t[0] for t in data_list]

    @staticmethod
    def __read_from_file(data_tuple: Tuple):
        file_data = data_tuple[0]
        cache_manager = data_tuple[1]
        if file_data.updated:
            file_name = str(os.path.join(
                cache_manager.get_directory(), file_data.file_name))
            try:
                df = FileHelper.read_parquet(file_name)

                # Fix the name of atm_in_usd here
                if ((file_data.data_type == DataType.HAIRCUT or file_data.data_type == DataType.MMR)
                        and 'atm_in_usd' in df.columns):
                    df.rename(
                        columns={'atm_in_usd': 'amt_in_usd'}, inplace=True)

                FileHelper.set_index(df, file_data.data_type)
                file_data.data = df
            except (FileNotFoundError, ValueError):
                cache_manager.remove(file_data)
                FileHelper.remove_file(file_name)
        else:
            file_list = cache_manager.get_file_list(file_data)
            for f in file_list:
                f.updated = True
            load_list = [(f, cache_manager) for f in file_list]
            Executor.submit(Client.__read_from_file, load_list)
            if file_list:
                df_list = [
                    f.data for f in file_list if f is not None and f.data is not None]
                if df_list:
                    df = pd.concat(df_list)
                    FileHelper.set_index(df, file_data.data_type)
                    df.sort_index(inplace=True)
                    file_data.data = df

    @exception_wrapper(NexusHubAPIError)
    def __load_from_hub(self,
                        exchange_type: str,
                        business_type: str,
                        data_type: DataType,
                        symbol: str,
                        hub_data_meta_list: List[ChunkData]):
        reqs = [{'exchange': exchange_type,
                 'business': business_type,
                 'category': data_type,
                 'sym': symbol,
                 'chunk': m} for m in hub_data_meta_list]
        Executor.submit(self.__request_hub_data, reqs)

    @exception_wrapper(NexusHubAPIError)
    def __load_streaming_from_hub(self, key: str, hub_data_meta_list: List[ChunkData]):
        reqs = [{'key': key,
                 'chunk': m} for m in hub_data_meta_list]
        Executor.submit(self.__request_hub_streaming_data, reqs)

    @exception_wrapper(NexusHubAPIError)
    def __load_sequenced_from_hub(self, key: str, hub_data_meta_list: List[ChunkData]):
        reqs = [{'key': key,
                 'chunk': m} for m in hub_data_meta_list]
        Executor.submit(self.__request_hub_sequenced_data, reqs)

    def __request_hub_data(self, fields: Dict):
        chunk_data = fields['chunk']
        data_request = ListRequest(exchange=fields['exchange'],
                                   business=fields['business'],
                                   category=fields['category'].name,
                                   sym=fields['sym'],
                                   start=chunk_data.start_time,
                                   end=chunk_data.end_time)
        data_response = self.__http_manager.data(data_request)
        df = SdkHelper.parse_data(data_response.data, fields['category'])
        chunk_data.confidence = data_response.confidence
        chunk_data.data = df

    def __request_hub_streaming_data(self, fields: Dict):
        chunk_data = fields['chunk']
        data_request = StreamingAndSequencedListRequest(key=fields['key'],
                                                        start=chunk_data.start_time,
                                                        end=chunk_data.end_time)
        data_response = self.__http_manager.streaming_data(data_request)
        df = SdkHelper.parse_data(data_response.data, DataType.STREAMING)
        chunk_data.confidence = Constants.MAX_CONFIDENCE
        chunk_data.data = df

    def __request_hub_sequenced_data(self, fields: Dict):
        chunk_data = fields['chunk']
        data_request = SequencedDataRequest(key=fields['key'],
                                            lower=chunk_data.start_time,
                                            upper=chunk_data.end_time)
        data_response = self.__http_manager.sequenced_data(data_request)
        df = SdkHelper.parse_data(data_response.data, DataType.SEQUENCED)
        chunk_data.confidence = Constants.MAX_CONFIDENCE
        chunk_data.data = df

    @staticmethod
    def __parse_data(data: list, dt: DataType) -> DataFrame:
        with StringIO('\n'.join(data)) as text_file:
            df = FileHelper.read_csv_file_with_data_type(text_file, dt)
            FileHelper.set_index(df, dt)
            return df

    @staticmethod
    def __validate_range(start: int, end: int):
        if start is not None and end is not None and start > end:
            raise ParamInvalidError(
                'end should be greater than or equal to start')

    @staticmethod
    def __validate_data_type(data_type: DataType):
        if not data_type.is_market_data():
            raise ParamInvalidError('Invalid data type for this method')

    @staticmethod
    def __generate_local_data_list(symbol: str,
                                   business_type: str,
                                   start_time: int,
                                   end_time: int,
                                   data_type: DataType,
                                   exchange_type: str,
                                   cache_manager: CacheManager) -> (List[FileMeta],
                                                                    List[ChunkData],
                                                                    List[ChunkData],
                                                                    bool):
        return cache_manager.get_meta_list(symbol,
                                           business_type,
                                           start_time,
                                           end_time,
                                           data_type,
                                           exchange_type) + (True,)

    @staticmethod
    def __parse_requested_symbol(requested_symbol: str) -> (str, DataType):
        parts = requested_symbol.split('.')
        if len(parts) != 2:
            raise ParamInvalidError('Invalid requested symbol')
        dt = parts[1].upper()
        if DataType.validate(dt):
            data_type = DataType[dt]
        else:
            raise ParamInvalidError('Invalid data type')
        return parts[0], data_type

    @staticmethod
    def __parse_full_symbol(full_symbol: str) -> (str, str, str):
        parts = full_symbol.split('_', 2)
        if len(parts) != 3:
            raise ParamInvalidError('invalid requested symbol')
        return parts[0], parts[1], parts[2]

    def __get_config(self,
                     missing_exception: Optional[bool] = None,
                     updated_exception: Optional[bool] = None,
                     local_first: Optional[bool] = None) -> Config:
        config = deepcopy(self.__config)
        if missing_exception is not None:
            config.missing_exception = missing_exception
        if updated_exception is not None:
            config.updated_exception = updated_exception
        if local_first is not None:
            config.local_first = local_first
        return config

    def __create_download_adapter(self) -> DownloadAdapter:
        if self.__config.http_download:
            return HttpDownloadAdapter(timeout=self.__config.api_timeout)
        return S3DownloadAdapter()

    @staticmethod
    def __type_validator(name: str, variable: any, clazz: type, nullable: bool = False):
        if type(nullable) is not bool:
            nullable = False
        if nullable and variable is None:
            return
        if isinstance(variable, clazz):
            return
        raise ParamInvalidError('invalid value for {}'.format(name))

    @staticmethod
    def __string_list_validator(name: str, lst: any, nullable: bool = False, empty: bool = False):
        if type(nullable) is not bool:
            nullable = False
        if type(empty) is not bool:
            nullable = False
        if nullable and lst is None:
            return
        if isinstance(lst, list):
            length = len(lst)
            if length == 0:
                if empty:
                    return
            elif all(isinstance(item, str) for item in lst):
                return
        raise ParamInvalidError('invalid value for {}'.format(name))

    @staticmethod
    def __value_validator(name: str, value: any, condition: str, threshold: any):
        is_valid = True
        match condition:
            case 'EQ':
                is_valid = value == threshold
            case 'NEQ':
                is_valid = value != threshold
            case 'GT':
                is_valid = value > threshold
            case 'GTE':
                is_valid = value >= threshold
            case 'LT':
                is_valid = value < threshold
            case 'LTE':
                is_valid = value <= threshold
            case 'INC':
                is_valid = str(threshold) in str(value)
            case 'EXC':
                is_valid = str(threshold) not in str(value)
        if not is_valid:
            raise ParamInvalidError('invalid value for {}. {} {} {}'.format(
                name, value, condition, threshold))

    @staticmethod
    def __types_validator(name: str, variable: any, clazz_list: List[type], nullable: bool = False):
        if type(nullable) is not bool:
            nullable = False
        if nullable and variable is None:
            return
        for clazz in clazz_list:
            if isinstance(variable, clazz):
                return
        raise ParamInvalidError('invalid value for {}'.format(name))

    def __validate_req_latest_seq_params(self, key: str, limit: int, updated_exception: Optional[bool]):
        self.__type_validator('key', key, str)
        self.__type_validator('limit', limit, int)
        if limit < 1:
            raise ParamInvalidError('limit should be greater than 0')
        self.__type_validator('updated_exception',
                              updated_exception, bool, nullable=True)

    def request_by_type(self,
                        exchange_type: str,
                        business_type: str,
                        symbol: str,
                        data_type: DataType,
                        start_time: int,
                        end_time: int = Constants.MAX_TIMESTAMP,
                        missing_exception: Optional[bool] = None,
                        updated_exception: Optional[bool] = None,
                        local_first: Optional[bool] = None) -> HubData:
        """
        Request data from the data hub.

        :param exchange_type: The requested exchange.
        :param business_type: The requested business type.
        :param symbol: The requested currency symbol.
        :param data_type: The requested data type.
        :param start_time: The start timestamp.
        :param end_time: The end timestamp.
        :param missing_exception: Indicate if raise exception when data is missing.
        :param updated_exception: Indicate if raise exception when any file fails to download.
        :param local_first: Request data from local cache first.
        :return: The requested data.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        :raises DataError: If requested data is not correct.
        """
        self.__type_validator('exchange_type', exchange_type, str)
        self.__type_validator('business_type', business_type, str)
        self.__type_validator('symbol', symbol, str)
        self.__type_validator('data_type', data_type, DataType)
        self.__type_validator('start_time', start_time, int)
        self.__type_validator('end_time', end_time, int)
        self.__type_validator('missing_exception',
                              missing_exception, bool, nullable=True)
        self.__type_validator('updated_exception',
                              updated_exception, bool, nullable=True)
        self.__type_validator('local_first', local_first, bool, nullable=True)
        self.__validate_range(start_time, end_time)
        self.__validate_data_type(data_type)
        exchange_type = exchange_type.upper()
        business_type = business_type.upper()
        symbol = symbol.upper()

        config = self.__get_config(local_first=local_first)

        if config.local_first and data_type != DataType.FUNDING_RATE:
            ret = None
            try:
                ret = self.__request(exchange_type,
                                     business_type,
                                     data_type, symbol,
                                     start_time,
                                     end_time,
                                     True,
                                     missing_exception,
                                     updated_exception)
            except SDKError:
                pass
            if (ret is not None and
                    not ret.missing and
                    len(ret.data) > 0 and
                    (end_time - ret.data.iloc[-1].name) < data_type.get_period_in_mill()):
                return ret

        return self.__request(exchange_type,
                              business_type,
                              data_type,
                              symbol,
                              start_time,
                              end_time,
                              False,
                              missing_exception,
                              updated_exception)

    def __request(self,
                  exchange_type: str,
                  business_type: str,
                  data_type: DataType,
                  symbol: str,
                  start_time: int,
                  end_time: int,
                  local_only: bool,
                  missing_exception: bool,
                  updated_exception: bool) -> HubData:
        # disable missing exception for funding rate, interest rate and open interest
        if not data_type.is_countable():
            missing_exception = False
        config = self.__get_config(
            missing_exception=missing_exception, updated_exception=updated_exception)
        full_path = os.path.join(
            self.__local_root_path, exchange_type, data_type.name, business_type, symbol)
        with CacheManager(full_path) as cache_manager:
            s3_meta_list, hub_meta_list, missing_meta_list, hub_data_loaded = self.__request_file_list(symbol,
                                                                                                       business_type,
                                                                                                       start_time,
                                                                                                       end_time,
                                                                                                       data_type,
                                                                                                       exchange_type,
                                                                                                       local_only,
                                                                                                       cache_manager)
            download_list = cache_manager.generate_download_list(
                s3_meta_list)
            Downloader(self.__download_adapter, full_path).download_files(
                download_list, self.__config.download_concurrency)
            self.__update_meta(download_list, s3_meta_list)
            cache_manager.update(s3_meta_list)
            s3_data_list = self.__read_from_files(s3_meta_list, cache_manager)
        if data_type.is_interest_rate_data():
            interest_rate_column_name = 'interest_rate'
            for d in s3_data_list:
                d.data[interest_rate_column_name] = d.data[interest_rate_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_mmr_data():
            mmr_column_name = 'mmr'
            for d in s3_data_list:
                d.data[mmr_column_name] = d.data[mmr_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_mmd_data():
            mmd_column_name = 'mmd'
            for d in s3_data_list:
                d.data[mmd_column_name] = d.data[mmd_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_haircut_data():
            haircut_column_name = 'haircut'
            for d in s3_data_list:
                d.data[haircut_column_name] = d.data[haircut_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_haircut_de_data():
            haircut_de_column_name = 'haircut_de'
            for d in s3_data_list:
                d.data[haircut_de_column_name] = d.data[haircut_de_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_pm_collateral_ratio_data():
            pm_collateral_ratio_column_name = 'pm_collateral_ratio'
            for d in s3_data_list:
                d.data[pm_collateral_ratio_column_name] = d.data[pm_collateral_ratio_column_name].map(
                    lambda c: c.tolist())
        elif data_type.is_glass_node_map_data():
            dict_column_name = 'o'
            for d in s3_data_list:
                d.data[dict_column_name] = d.data[dict_column_name].map(
                    lambda c: {k: DECIMAL_STORAGE_TYPE(v) for k, v in c.items()})
        elif data_type.is_event_data():
            events_column_name = 'events'
            for d in s3_data_list:
                d.data[events_column_name] = d.data[events_column_name].map(
                    lambda c: c.tolist())
        if not hub_data_loaded:
            self.__load_from_hub(
                exchange_type, business_type, data_type, symbol, hub_meta_list)
        full_symbol = '{}_{}_{}'.format(exchange_type, business_type, symbol)
        DataValidator.validate_missing(
            full_symbol, data_type, s3_data_list, hub_meta_list, missing_meta_list, config)
        expected_timestamps = self.__databento_kline_trading_hours(
            exchange_type, business_type, symbol, data_type, start_time, end_time, local_only)
        return DataAggregator().aggregate(full_symbol, data_type, start_time, end_time, s3_data_list,
                                          hub_meta_list, missing_meta_list, config,
                                          expected_timestamps=expected_timestamps)

    def __databento_kline_trading_hours(self,
                                        exchange_type: str,
                                        business_type: str,
                                        symbol: str,
                                        data_type: DataType,
                                        start_time: int,
                                        end_time: int,
                                        local_only: bool) -> Optional[List[int]]:
        """
        For DataBento KLINE_1H, return the trading-hour start-timestamps (ms) in
        [start_time, end_time] per EVENT_1H's ``is_trading`` field (forward-filled).
        Returns ``None`` for every other (exchange, data_type) combination and for
        local-only reads.

        When ``end_time`` is ``Constants.MAX_TIMESTAMP`` (best-effort), the trading-hour
        list is capped to the bar containing the last observed EVENT_1H row —
        extrapolating past EVENT_1H coverage would either over-include (forward-filling
        'Y' indefinitely) or under-include (forward-filling 'N' through hours that kline
        actually has data for).

        The EVENT_1H fetch is widened by 7 days (floored at
        ``DATABENTO_MIN_EVENT_START_MS``) so forward-fill has prior context when the
        requested range starts mid-session. Raises ``DataError`` when no events are
        found even with that lookback — the trading hours cannot be determined.
        """
        if local_only or data_type != DataType.KLINE_1H or exchange_type != 'DATABENTO':
            return None

        period = data_type.get_period_in_mill()
        lookback_ms = 7 * 24 * 3600 * 1000
        max_event_start = (
            DateTimeHelper.now_epoch_milliseconds() // period - 1) * period
        events_fetch_start = max(
            start_time - lookback_ms, DATABENTO_MIN_EVENT_START_MS)
        if start_time < DATABENTO_MIN_EVENT_START_MS:
            start_time = DATABENTO_MIN_EVENT_START_MS
        if end_time > max_event_start:
            end_time = max_event_start
        if start_time > end_time:
            return []

        events = self.request_by_type(exchange_type, business_type, symbol,
                                      DataType.EVENT_1H, events_fetch_start, end_time,
                                      missing_exception=False,
                                      updated_exception=False,
                                      local_first=False)
        if events.data is None or len(events.data) == 0 or not events.updated:
            raise DataError(
                'Failed to fetch EVENT_1H to determine trading hours')

        return self.__list_trading_hours(events.data, events_fetch_start, start_time, end_time)

    @staticmethod
    def __list_trading_hours(events_df: DataFrame,
                             fetch_start_time: int,
                             start_time: int,
                             end_time: int) -> List[int]:
        """
        Return trading-hour start-timestamps (ms) in [start_time, end_time] from EVENT_1H.
        Per hour bucket: if any exploded event has ``is_trading == 'Y'`` the hour is 'Y'
        (Y dominates); else if any has 'N' the hour is 'N'; else (no events) the hour
        inherits the previous hour's state via forward-fill. ``fetch_start_time`` is the
        earliest hour the caller actually fetched events for (typically
        ``start_time - lookback``) — reindex extends from that point so the forward-fill
        is seeded by pre-range events. Final list covers only hours in
        [start_time, end_time].
        """
        period = DataType.KLINE_1H.get_period_in_mill()
        period_ns = period * 1_000_000
        fetch_first_hour = (fetch_start_time // period) * period
        last_hour = (end_time // period) * period

        exploded = events_df['events'].explode().dropna()
        if len(exploded) == 0:
            return []
        # Vectorized extraction: one list comprehension per column, no per-row Series.map.
        ts_event_ns = np.array(
            [int(ev['hd']['ts_event']) for ev in exploded], dtype='int64')
        flag_values = np.array(
            [ev.get('is_trading') for ev in exploded], dtype=object)
        flags = pd.Series(flag_values, index=ts_event_ns, dtype=object)

        # Splice NaN placeholders at the chronological positions of hours absent from
        # ``flags``. ``np.setdiff1d`` is faster than ``Index.difference``; ``searchsorted``
        # assumes ``flags.index`` is non-decreasing (true when events come back in ts_event
        # order from Databento).
        all_hours_ns = np.arange(
            fetch_first_hour, last_hour + period, period, dtype='int64') * 1_000_000
        missing_arr = np.setdiff1d(
            all_hours_ns, flags.index.values, assume_unique=False)
        if len(missing_arr) > 0:
            positions = np.searchsorted(flags.index.values, missing_arr)
            new_idx = np.insert(flags.index.values, positions, missing_arr)
            new_vals = np.insert(flags.values, positions, None)
            flags = pd.Series(new_vals, index=new_idx, dtype=object)
        flags = flags.ffill()

        # Bucket by hour and reduce with a vectorized ``.any()`` (single C-level groupby
        # call) — replaces the per-group Python ``apply(lambda)`` which dominated runtime.
        hour_idx = flags.index.values // period_ns * period
        is_y = (flags.values == 'Y')
        per_hour_is_y = pd.Series(is_y, index=hour_idx).groupby(level=0).any()
        mask = (per_hour_is_y.index >= start_time) & (
            per_hour_is_y.index <= end_time)
        in_range = per_hour_is_y[mask]
        return in_range.index[in_range.values].astype('int64').tolist()

    def request(self,
                requested_symbol: str,
                start_time: int,
                end_time: int = Constants.MAX_TIMESTAMP,
                missing_exception: Optional[bool] = None,
                updated_exception: Optional[bool] = None,
                local_first: Optional[bool] = None) -> HubData:
        """
        Request data from the data hub.

        :param requested_symbol: The requested symbol.
        :param start_time: The start timestamp.
        :param end_time: The end timestamp.
        :param missing_exception: Indicate if raise exception when data is missing.
        :param updated_exception: Indicate if raise exception when any file fails to download.
        :param local_first: Request data from local cache first.
        :return: The requested data.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        :raises DataError: If requested data is not correct.
        """
        self.__type_validator('requested_symbol', requested_symbol, str)
        self.__type_validator('start_time', start_time, int)
        self.__type_validator('end_time', end_time, int)
        self.__type_validator('missing_exception',
                              missing_exception, bool, nullable=True)
        self.__type_validator('updated_exception',
                              updated_exception, bool, nullable=True)
        self.__type_validator('local_first', local_first, bool, nullable=True)
        full_symbol, data_type = self.__parse_requested_symbol(
            requested_symbol)
        if data_type.is_market_data():
            exchange_type, business_type, symbol = self.__parse_full_symbol(
                full_symbol)
            return self.request_by_type(exchange_type,
                                        business_type,
                                        symbol,
                                        data_type,
                                        start_time,
                                        end_time,
                                        missing_exception,
                                        updated_exception,
                                        local_first)
        raise ParamInvalidError(
            'Only defined market data is accepted for data type')

    def file_upload(self,
                    key: str,
                    version: int,
                    file: [str | bytes],
                    file_type: str,
                    delimiter: str = '_',
                    expiry_in: Optional[int] = None) -> Notebook:
        """
        Upload the factor file to data hub.

        :param key: The key of upload file.
        :param version: The version of the file.
        :param file: The file name with directory or the content of the file.
        :param file_type: The type of the file.
        :param delimiter: The delimiter of the key, to generate S3 prefix. Default is '_'.
        :param expiry_in: The expiry of the index in second. Default is 'None'.
        when key, fileType and version conflicts. Default is False.
        :return: A Notebook object.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('version', version, int)
        self.__types_validator('file', file, [str, bytes])
        self.__type_validator('file_type', file_type, str)
        self.__type_validator('delimiter', delimiter, str)
        self.__type_validator('expiry_in', expiry_in, int, nullable=True)
        self.__value_validator('delimiter', delimiter, 'EXC', '/')
        self.__value_validator('key', key, 'EXC', '/')
        is_path = isinstance(file, str)
        is_data = isinstance(file, bytes)
        if not (is_path or is_data):
            raise ParamInvalidError('Unsupported file object')
        if is_path:
            FileHelper.validate_file_exists(file)
            fingerprint = FileHelper.checksum(
                file, Constants.CHECKSUM_SHA256)
        else:
            fingerprint = FileHelper.sha256(file)
        note_book_request = NotebookRequest(key=key,
                                            version=version,
                                            fingerprint=fingerprint,
                                            delimiter=delimiter,
                                            file_type=file_type,
                                            fingerprint_algorithm=Constants.CHECKSUM_SHA256,
                                            expiry_in=expiry_in,
                                            override_enabled=False,
                                            uploaded=False)
        pre_signed_response = self.__http_manager.notebook_pre_signed(
            note_book_request)
        try:
            if is_path:
                self.__http_manager.http_upload(file, fingerprint,
                                                pre_signed_response.url)
            else:
                self.__http_manager.http_upload_binary(file, fingerprint,
                                                       pre_signed_response.url)
            note_book_request.uploaded = True
            upload_except = None
        except Exception as e:
            note_book_request.uploaded = False
            upload_except = e
        finally:
            notebook = self.__http_manager.notebook_commit(note_book_request)
        if notebook is not None:
            return notebook.to_notebook(None)
        raise FileOperationError('Failed to upload file to S3. {}'.format(
            '' if upload_except is None else str(upload_except)))

    def file_download(self,
                      key: str,
                      file_type: str,
                      lower_bound: Optional[int] = None,
                      upper_bound: Optional[int] = None,
                      limit: Optional[int] = None,
                      sort_direction: str = 'DESC',
                      local_first: Optional[bool] = None) -> List[Notebook]:
        """
        Get Notebook by key.

        :param key: The key of the notebook.
        :param file_type: The type of the notebook.
        :param lower_bound: The lower bound of version.
        :param upper_bound: The upper bound of version.
        :param limit: The number of notebooks.
        :param sort_direction: The select direction of notebooks, default is DESC.
        :return: The list of Notebook objects.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('file_type', file_type, str)
        self.__type_validator('lower_bound', lower_bound, int, nullable=True)
        self.__type_validator('upper_bound', upper_bound, int, nullable=True)
        self.__type_validator('limit', limit, int, nullable=True)
        self.__type_validator('sort_direction', sort_direction, str)
        self.__type_validator('local_first', local_first, bool, nullable=True)

        exchange_type = 'CYBERX'
        symbol = 'ALL'
        full_path = os.path.join(
            self.__local_root_path, exchange_type, DataType.NOTEBOOK.name,
            '{}_{}'.format(key, file_type), symbol)
        download_path = os.path.join(self.__local_root_path, 'download')
        if local_first:
            with CacheManager(full_path) as cm:
                meta_list = cm.get_meta_list_from_cache(
                    exchange_type, DataType.NOTEBOOK, key, symbol)
                if len(meta_list) > 0:
                    notebook_list = [meta.to_notebook(
                        file_type, download_path) for meta in meta_list]
                    if lower_bound is not None:
                        notebook_list = [
                            notebook for notebook in notebook_list if notebook.version >= lower_bound]
                    if upper_bound is not None:
                        notebook_list = [
                            notebook for notebook in notebook_list if notebook.version <= upper_bound]
                    if sort_direction == 'ASC':
                        notebook_list.sort(key=lambda x: x.version)
                    else:
                        notebook_list.sort(
                            key=lambda x: x.version, reverse=True)
                    if limit is not None:
                        notebook_list = notebook_list[:limit]
                    if len(notebook_list) > 0:
                        return notebook_list

        notebook_list_response = self.__http_manager.notebook_list(NotebookListRequest(
            key=key,
            file_type=file_type,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            limit=limit,
            sort_direction=sort_direction.upper()))
        with CacheManager(full_path) as cache_manager:
            meta_list = list()
            name_map = dict()
            for notebook in notebook_list_response:
                file_name = Constants.DATA_FILE_NAME_TEMPLATE.format(
                    exchange_type, key, DataType.NOTEBOOK.name,
                    symbol, notebook.version, notebook.version)
                meta_list.append(FileMeta(exchange_type=exchange_type,
                                          business_type=key,
                                          data_type=DataType.NOTEBOOK.name,
                                          symbol=symbol,
                                          start_time=notebook.version,
                                          end_time=notebook.version,
                                          file_name=file_name,
                                          file_type=FileType.NOTEBOOK,
                                          finger_print=notebook.fingerprint,
                                          confidence=-1,
                                          expire_time=-1,
                                          url=notebook.url))
                name_map[os.path.join(full_path, file_name)] = notebook.to_notebook(
                    download_path)
            download_list = cache_manager.generate_download_list(meta_list)
            Downloader(self.__download_adapter, full_path).download_files(
                download_list, self.__config.download_concurrency)
            self.__update_meta(download_list, meta_list)
            cache_manager.update(meta_list)
        FileHelper.make_dir(download_path)
        for src, desc in name_map.items():
            FileHelper.link_file(src, os.path.join(
                desc.file_path, desc.file_name))
        return [v for v in name_map.values()]

    def streaming_commit(self,
                         key: str,
                         content: str,
                         seq_number: int,
                         content_type: str,
                         package_frequency: str = 'DAILY',
                         start_time: Optional[int] = None,
                         end_time: Optional[int] = None):
        """
        Upload streaming records to data hub.

        :param key: The key of the upload record.
        :param content: The content of the record.
        :param seq_number: The sequence number of the record.
        :param content_type: The content type of the record.
        :param package_frequency: The package frequency of records. Default is 'DAILY'.
        :param start_time: The start time of the record. Default is 'None'.
        :param end_time: The end time of the record. Default is 'None'.
        :raises ParamInvalidError: If parameter is invalid.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('content', content, str)
        self.__type_validator('seq_number', seq_number, int)
        self.__type_validator('content_type', content_type, str)
        self.__type_validator('package_frequency', package_frequency, str)
        self.__type_validator('start_time', start_time, int, nullable=True)
        self.__type_validator('end_time', end_time, int, nullable=True)
        self.__value_validator('key', key, 'EXC', '/')
        start = start_time if start_time is not None else DateTimeHelper.now_epoch_milliseconds()
        end = end_time if start_time is not None and end_time is not None else start
        self.__http_manager.streaming_commit(StreamingData(key=key,
                                                           content=content,
                                                           seq_number=seq_number,
                                                           content_type=content_type,
                                                           package_frequency=package_frequency,
                                                           start_time=start,
                                                           end_time=end))

    def request_streaming_data(self,
                               key: str,
                               start_time: int,
                               end_time: int = Constants.MAX_TIMESTAMP,
                               updated_exception: Optional[bool] = None) -> HubData:
        """
        Request data from the data hub.

        :param key: The requested key of records.
        :param start_time: The start timestamp of the records.
        :param end_time: The end timestamp of the records.
        :param updated_exception: Indicate if raise exception when any file fails to download.
        :return: The requested data.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        :raises DataError: If requested data is not correct.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('start_time', start_time, int)
        self.__type_validator('end_time', end_time, int)
        self.__type_validator('updated_exception',
                              updated_exception, bool, nullable=True)
        self.__validate_range(start_time, end_time)
        exchange_type = Constants.EXCHANGE_CYBERX
        data_type = DataType.STREAMING
        business_type = key
        symbol = Constants.SYMBOL_ALL
        config = self.__get_config(updated_exception=updated_exception)
        full_path = os.path.join(
            self.__local_root_path, exchange_type, data_type.name, business_type, symbol)
        s3_meta_list, hub_meta_list = self.__request_streaming_file_list(key,
                                                                         start_time,
                                                                         end_time)
        with CacheManager(full_path) as cache_manager:
            download_list = cache_manager.generate_download_list(
                s3_meta_list)
            Downloader(self.__download_adapter, full_path).download_files(
                download_list, self.__config.download_concurrency)
            self.__update_meta(download_list, s3_meta_list)
            cache_manager.update(s3_meta_list)
            s3_data_list = self.__read_from_files(s3_meta_list, cache_manager)

        self.__load_streaming_from_hub(key, hub_meta_list)
        return DataAggregator().aggregate_streaming_and_sequenced(key,
                                                                  start_time,
                                                                  end_time,
                                                                  data_type,
                                                                  s3_data_list,
                                                                  hub_meta_list,
                                                                  config)

    def kv_set(self,
               key: str,
               value: str,
               ttl: Optional[int] = None) -> CacheResponse:
        """
        Upload key-value cache data to data hub.

        :param key: The key of the cache data.
        :param value: The value of the cache data.
        :param ttl: The time to live of the cache data.
        :return: A CacheResponse object including the key and the set result.
        :raises ParamInvalidError: If parameter is invalid.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('value', value, str)
        self.__type_validator('ttl', ttl, int, nullable=True)
        return self.__http_manager.cache_set(CacheSetRequest(key=key, value=value, ttl=ttl))

    def kv_get(self, key: str) -> CacheResponse:
        """
        Request key-value cache data from data hub.

        :param key: The key of the cache data.
        :return: A CacheResponse object including the key and value.
        :raises ParamInvalidError: If parameter is invalid.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        return self.__http_manager.cache_get(key)

    def sequenced_commit(self,
                         key: str,
                         contents: List[str],
                         content_type: str,
                         pre_seq_number: Optional[int] = None) -> List[SequencedData]:
        """
        Upload sequenced records to data hub.

        :param key: The key of the upload record.
        :param contents: The list of records. The records will be committed in order in the list.
        :param content_type: The content type of the record.
        :param pre_seq_number: The sequence number of the record that this record is based on.
        :raises ParamInvalidError: If parameter is invalid.
        :return: A list of sequenced records with assigned sequence numbers.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key', key, str)
        self.__string_list_validator('contents', contents)
        self.__type_validator('content_type', content_type, str)
        self.__type_validator(
            'pre_seq_number', pre_seq_number, int, nullable=True)
        self.__value_validator('key', key, 'EXC', '/')
        return self.__http_manager.sequenced_commit(SequencedCommitData(key=key,
                                                                        contents=contents,
                                                                        content_type=content_type,
                                                                        pre_seq_number=pre_seq_number))

    def request_sequenced_data(self,
                               key: str,
                               start_seq_number: int,
                               end_seq_number: Optional[int] = Constants.MAX_INTEGER,
                               updated_exception: Optional[bool] = None) -> HubData:
        """
        Request sequenced data from the data hub.

        :param key: The requested key of records.
        :param start_seq_number: The start seq number of the records.
        :param end_seq_number: The end seq number of the records.
        :param updated_exception: Indicate if raise exception when any file fails to download.
        :return: The requested data.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        :raises DataError: If requested data is not correct.
        """
        self.__type_validator('key', key, str)
        self.__type_validator('start_seq_number', start_seq_number, int)
        self.__type_validator(
            'end_seq_number', end_seq_number, int, nullable=True)
        self.__type_validator('updated_exception',
                              updated_exception, bool, nullable=True)
        self.__validate_range(start_seq_number, end_seq_number)
        exchange_type = Constants.EXCHANGE_CYBERX
        data_type = DataType.SEQUENCED
        business_type = key
        symbol = Constants.SYMBOL_ALL
        config = self.__get_config(updated_exception=updated_exception)
        full_path = os.path.join(
            self.__local_root_path, exchange_type, data_type.name, business_type, symbol)
        s3_meta_list, hub_meta_list = self.__request_sequenced_streaming_file_list(key,
                                                                                   start_seq_number,
                                                                                   end_seq_number)
        with CacheManager(full_path) as cache_manager:
            download_list = cache_manager.generate_download_list(
                s3_meta_list)
            Downloader(self.__download_adapter, full_path).download_files(
                download_list, self.__config.download_concurrency)
            self.__update_meta(download_list, s3_meta_list)
            cache_manager.update(s3_meta_list)
            s3_data_list = self.__read_from_files(s3_meta_list, cache_manager)

        self.__load_sequenced_from_hub(key, hub_meta_list)
        return DataAggregator().aggregate_streaming_and_sequenced(key,
                                                                  start_seq_number,
                                                                  end_seq_number,
                                                                  data_type,
                                                                  s3_data_list,
                                                                  hub_meta_list,
                                                                  config)

    def request_latest_sequenced_data(self,
                                      key: str,
                                      limit: int = 1,
                                      updated_exception: Optional[bool] = None) -> HubData:
        """
        Request latest sequenced data from the data hub in desc sequence number order.

        :param key: The requested key of records.
        :param limit: The number of the records in desc order.
        :param updated_exception: Indicate if raise exception when any file fails to download.
        :return: The requested data.
        :raises ParamInvalidError: If parameter is invalid.
        :raises FileOperationError: If file operation is failed.
        :raises DownloadError: If file download is failed.
        :raises NexusHubAPIError: If data hub API is failed.
        :raises DataError: If requested data is not correct.
        """
        self.__validate_req_latest_seq_params(key, limit, updated_exception)

        exchange_type = Constants.EXCHANGE_CYBERX
        data_type = DataType.SEQUENCED
        business_type = key
        symbol = Constants.SYMBOL_ALL
        config = self.__get_config(updated_exception=updated_exception)
        full_path = os.path.join(
            self.__local_root_path, exchange_type, data_type.name, business_type, symbol)

        s3_meta_list, hub_data_list = self.__request_sequenced_streaming_latest(
            key, limit)
        hub_df = SdkHelper.parse_data(hub_data_list, DataType.SEQUENCED)
        remain = limit - len(hub_df)

        all_updated, s3_df = self.__retrieve_s3_latest_seq_data(
            full_path, remain, s3_meta_list)

        df = pd.concat([s3_df, hub_df])
        df.sort_index(ascending=False, inplace=True)
        return_data = HubData(missing=False,
                              updated=all_updated,
                              data=df.head(limit))
        DataValidator.validate_data(key, data_type, return_data, config)
        return return_data

    def request_kline_detail(self,
                             exchange: Optional[str] = None,
                             business: Optional[str] = None,
                             category: Optional[str] = None,
                             sym: Optional[str] = None) -> Generator[List[KlineDetail]]:
        """
        Request kline detail data from data hub.

        :param exchange: The exchange name.
        :param business: The business type.
        :param category: The data type.
        :param sym: The symbol name.
        :return: The generator to get the requested kline detail data.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('exchange', exchange, str, nullable=True)
        self.__type_validator('business', business, str, nullable=True)
        self.__type_validator('category', category, str, nullable=True)
        self.__type_validator('sym', sym, str, nullable=True)
        page_size = Constants.PAGE_SIZE
        is_exchange_null = exchange is None
        is_business_null = business is None
        is_category_null = category is None
        is_sym_null = sym is None
        # Check if exchange, business, category and sym all are None
        if ((is_exchange_null and is_business_null and is_category_null and is_sym_null) !=
                (is_exchange_null or is_business_null or is_category_null or is_sym_null)):
            raise ParamInvalidError(
                'exchange, business, category and sym should be assigned or not')
        resp = self.__http_manager.kline_detail(KlineDetailRequest(curPage=0,
                                                                   pageSize=page_size,
                                                                   exchange=exchange,
                                                                   business=business,
                                                                   category=category,
                                                                   sym=sym))
        yield resp.resources
        reqs = [KlineDetailRequest(curPage=i,
                                   pageSize=page_size,
                                   exchange=exchange,
                                   business=business,
                                   category=category,
                                   sym=sym) for i in self.__generate_next_range(resp)]
        for req in reqs:
            resp = self.__http_manager.kline_detail(req)
            if resp is not None:
                yield resp.resources

    def request_streaming_detail(self, key: Optional[str] = None) -> Generator[List[StreamingAndSequencedDetail]]:
        """
        Request streaming detail data from data hub.

        :param key: The requested key pattern, default is None.
        :return: The generator to get the requested streaming detail data.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        page_size = Constants.PAGE_SIZE
        self.__type_validator('key', key, str, nullable=True)
        resp = self.__http_manager.streaming_detail(DetailByKeyRequest(curPage=0,
                                                                       pageSize=page_size,
                                                                       key=key))
        yield resp.resources
        reqs = [DetailByKeyRequest(curPage=i,
                                   pageSize=page_size,
                                   key=key) for i in self.__generate_next_range(resp)]
        for req in reqs:
            resp = self.__http_manager.streaming_detail(req)
            if resp is not None:
                yield resp.resources

    def request_sequenced_detail(self, key: Optional[str] = None) -> Generator[List[StreamingAndSequencedDetail]]:
        """
        Request sequenced detail data from data hub.

        :param key: The requested key pattern, default is None.
        :return: The generator to get the requested sequenced detail data.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        page_size = Constants.PAGE_SIZE
        self.__type_validator('key', key, str, nullable=True)
        resp = self.__http_manager.sequenced_detail(DetailByKeyRequest(curPage=0,
                                                                       pageSize=page_size,
                                                                       key=key))
        yield resp.resources
        reqs = [DetailByKeyRequest(curPage=i,
                                   pageSize=page_size,
                                   key=key) for i in self.__generate_next_range(resp)]
        for req in reqs:
            resp = self.__http_manager.sequenced_detail(req)
            if resp is not None:
                yield resp.resources

    def request_notebook_detail(self, key: Optional[str] = None) -> Generator[List[NotebookDetail]]:
        """
        Request notebook detail data from data hub.

        :param key: The requested key pattern, default is None.
        :return: The generator to get the requested notebook detail data.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        page_size = Constants.PAGE_SIZE
        self.__type_validator('key', key, str, nullable=True)
        resp = self.__http_manager.notebook_detail(DetailByKeyRequest(curPage=0,
                                                                      pageSize=page_size,
                                                                      key=key))
        yield resp.resources
        reqs = [DetailByKeyRequest(curPage=i,
                                   pageSize=page_size,
                                   key=key) for i in self.__generate_next_range(resp)]
        for req in reqs:
            resp = self.__http_manager.notebook_detail(req)
            if resp is not None:
                yield resp.resources

    def request_streaming_key_by_limit(self,
                                       key_prefix: Optional[str] = None,
                                       start_key: Optional[str] = None,
                                       included: bool = False,
                                       limit: int = 100) -> List[str]:
        """
        Request streaming data keys from data hub.

        :param key_prefix: The prefix of keys, default is None.
        :param start_key: The start key of the range, default is None.
        :param included: If the start key is included in the range.
        :param limit: The max number of keys, default is 100.
        :return: The list of keys.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key_prefix', key_prefix, str, nullable=True)
        self.__type_validator('start_key', start_key, str, nullable=True)
        self.__type_validator('included', included, bool)
        self.__type_validator('limit', limit, int)
        if key_prefix is not None:
            self.__value_validator('key_prefix', key_prefix, 'EXC', '*')
        if start_key is not None:
            self.__value_validator('start_key', start_key, 'EXC', '*')
        return self.__http_manager.streaming_limited_keys(KeyAndLimitRequest(key=key_prefix,
                                                                             start=start_key,
                                                                             included=included,
                                                                             limit=limit))

    def request_sequenced_key_by_limit(self,
                                       key_prefix: Optional[str] = None,
                                       start_key: Optional[str] = None,
                                       included: bool = False,
                                       limit: int = 100) -> List[str]:
        """
        Request sequenced data keys from data hub.

        :param key_prefix: The prefix of keys, default is None.
        :param start_key: The start key of the range, default is None.
        :param included: If the start key is included in the range.
        :param limit: The max number of keys, default is 100.
        :return: The list of keys.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__type_validator('key_prefix', key_prefix, str, nullable=True)
        self.__type_validator('start_key', start_key, str, nullable=True)
        self.__type_validator('included', included, bool)
        self.__type_validator('limit', limit, int)
        if key_prefix is not None:
            self.__value_validator('key_prefix', key_prefix, 'EXC', '*')
        if start_key is not None:
            self.__value_validator('start_key', start_key, 'EXC', '*')
        return self.__http_manager.sequenced_limited_keys(KeyAndLimitRequest(key=key_prefix,
                                                                             start=start_key,
                                                                             included=included,
                                                                             limit=limit))

    def request_streaming_detail_by_key(self, keys: list[str]) -> List[StreamingAndSequencedBaseDetail]:
        """
        Request streaming detail data from data hub.

        :param keys: The list of keys.
        :return: The streaming detail data according to the keys.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__string_list_validator('keys', keys)
        return self.__http_manager.streaming_limited_details(KeysRequest(keys=keys))

    def request_sequenced_detail_by_key(self, keys: list[str]) -> List[StreamingAndSequencedBaseDetail]:
        """
        Request sequenced detail data from data hub.

        :param keys: The list of keys.
        :return: The sequenced detail data according to the keys.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        self.__string_list_validator('keys', keys)
        return self.__http_manager.sequenced_limited_details(KeysRequest(keys=keys))

    def __retrieve_s3_latest_seq_data(self,
                                      full_path: str,
                                      remain: int,
                                      s3_meta_list: List[FileMeta]) -> (bool, DataFrame):
        s3_meta_list_length = len(s3_meta_list)
        all_updated = True
        s3_df = pd.DataFrame(
            columns=['sequence_number', 'content_type', 'content'])
        if remain > 0 and s3_meta_list_length > 0:
            desc_s3_list = sorted(
                s3_meta_list, key=lambda x: x.start_time, reverse=True)
            index = 0
            while remain > 0 and index < s3_meta_list_length:
                total = 0
                s3_download_list = list()
                while index < s3_meta_list_length:
                    item = desc_s3_list[index]
                    if total < remain:
                        s3_download_list.insert(0, item)
                        total = total + (item.end_time - item.start_time + 1)
                        all_updated = all_updated and item.updated
                        index = index + 1
                    else:
                        break
                with CacheManager(full_path) as cache_manager:
                    download_list = cache_manager.generate_download_list(
                        s3_download_list)
                    Downloader(self.__download_adapter, full_path).download_files(
                        download_list, self.__config.download_concurrency)
                    self.__update_meta(download_list, s3_download_list)
                    cache_manager.update(s3_download_list)
                    s3_data_list = self.__read_from_files(
                        s3_download_list, cache_manager)
                s3_df = pd.concat(
                    [item.data for item in s3_data_list] + [s3_df])
                remain = remain - len(s3_df)
        return all_updated, s3_df

    @staticmethod
    def __generate_next_range(page_info: PageResponseBase):
        return range(page_info.curPage + 1, page_info.totalPage)

    def get_meta_symbols(self, symbol_list: List[str]) -> List[MetaSymbol]:
        """
        Request meta symbols from data hub.

        :param symbol_list : The list of symbols required.
        :return: The list of MetaSymbol.
        :raises NexusHubAPIError: If data hub API is failed.
        """
        return self.__http_manager.get_meta_symbols(symbol_list)
