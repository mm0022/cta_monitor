from typing import Dict, List, Optional

import pandas as pd
from pandas import DataFrame

from nexus_data_hub_sdk.exception.exceptions import NexusHubAPIError
from nexus_data_hub_sdk.client.config import Config
from nexus_data_hub_sdk.aggregator.data_validator import DataValidator
from nexus_data_hub_sdk.client.hub_data import HubData
from nexus_data_hub_sdk.share.models import FileData, ChunkData
from nexus_data_hub_sdk.share.enums import DataType


class DataAggregator:
    def __init__(self):
        self.__all_updated = True
        self.__end_time = 0

    def aggregate(self,
                  full_symbol: str,
                  data_type: DataType,
                  start_time: int,
                  end_time: int,
                  s3_data: List[FileData],
                  hub_data: List[ChunkData],
                  missing_data: List[ChunkData],
                  config: Config,
                  expected_timestamps: Optional[List[int]] = None) -> HubData:
        self.__all_updated = True
        self.__end_time = 0
        data_map = dict()
        cursor_in_s3_data = self.__append_data_map_and_get_cursor_by_start_time(
            data_map, s3_data, start_time)
        cursor_in_hub_data = self.__append_data_map_and_get_cursor_by_start_time(
            data_map, hub_data, start_time)
        cursor_in_missing_data = self.__append_data_map_and_get_cursor_by_start_time(
            data_map, missing_data, start_time)
        if cursor_in_s3_data:
            cursor = cursor_in_s3_data
        elif cursor_in_hub_data:
            cursor = cursor_in_hub_data
        else:
            cursor = cursor_in_missing_data
        df_list = list()
        chunk_count = 0
        while cursor and cursor.start_time <= end_time:
            chunk_count = chunk_count + 1
            if cursor.data is not None and len(cursor.data) > 0:
                # Only filter data that has start_time column
                if 'start_time' in cursor.data.columns:
                    filtered_df = cursor.data[(start_time <= cursor.data.index) & (
                        cursor.data.index <= end_time)]
                else:
                    filtered_df = cursor.data
                df_list.append(filtered_df)
            cursor = data_map.get(cursor.end_time + 1, None)
        if chunk_count != len(data_map):
            raise NexusHubAPIError('Abnormal data hub data list response')
        if len(df_list) > 0:
            concat_list = pd.concat(df_list)
        else:
            concat_list = DataFrame()
        return_value = HubData(missing=DataValidator.verify_length(data_type,
                                                                   start_time,
                                                                   min(self.__end_time,
                                                                       end_time),
                                                                   concat_list,
                                                                   expected_timestamps),
                               updated=DataValidator.verify_update_status(
                                   self.__all_updated),
                               data=concat_list)
        DataValidator.validate_data(
            full_symbol, data_type, return_value, config)
        return return_value

    def aggregate_streaming_and_sequenced(self,
                                          key: str,
                                          start: int,
                                          end: int,
                                          data_type: DataType,
                                          s3_data: List[FileData],
                                          hub_data: List[ChunkData],
                                          config: Config) -> HubData:
        self.__all_updated = True
        all_list = s3_data + hub_data
        all_list = sorted(all_list, key=lambda x: x.start_time)
        df_list = list()
        for d in all_list:
            if isinstance(d, FileData):
                if d.data is None or not d.updated:
                    self.__all_updated = False
            elif isinstance(d, ChunkData):
                if d.data is None:
                    self.__all_updated = False
            if d.data is not None:
                df_list.append(d.data)
        if len(df_list) > 0:
            concat_list = pd.concat(df_list)
        else:
            concat_list = DataFrame()
        filtered_df = concat_list[(start <= concat_list.index) & (
            concat_list.index <= end)]
        return_data = HubData(missing=False,
                              updated=DataValidator.verify_update_status(
                                  self.__all_updated),
                              data=filtered_df)
        DataValidator.validate_data(
            key, data_type, return_data, config)
        return return_data

    def __append_data_map_and_get_cursor_by_start_time(self,
                                                       data_map: Dict,
                                                       data_list: List[FileData | ChunkData],
                                                       start_time: int) -> Optional[FileData | ChunkData]:
        ret = None
        # Check if all chunk updated
        for v in data_list:
            if isinstance(v, FileData):
                if v.data is None or not v.updated:
                    self.__all_updated = False
            elif isinstance(v, ChunkData):
                if not v.missing and v.data is None:
                    self.__all_updated = False
            self.__end_time = max(v.end_time, self.__end_time)
            data_map[v.start_time] = v
            if v.start_time <= start_time <= v.end_time:
                ret = v
        return ret
