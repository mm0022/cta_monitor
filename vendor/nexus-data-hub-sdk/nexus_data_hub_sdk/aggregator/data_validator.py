from typing import List, Optional

from pandas import DataFrame

from nexus_data_hub_sdk.client.config import Config
from nexus_data_hub_sdk.share.enums import DataType
from nexus_data_hub_sdk.exception.exceptions import DataError
from nexus_data_hub_sdk.client.hub_data import HubData
from nexus_data_hub_sdk.share.models import ChunkData, FileData


class DataValidator:
    @staticmethod
    def is_gap_tolerant(full_symbol: str, data_type: DataType) -> bool:
        return full_symbol.startswith('DATABENTO_FUT') and data_type in [DataType.KLINE_1H, DataType.EVENT_1H]

    @staticmethod
    def verify_length(data_type: DataType,
                      start_time: int,
                      end_time: int,
                      data_frame: DataFrame,
                      expected_timestamps: Optional[List[int]] = None) -> bool:
        if not data_type.is_countable():
            return False
        if expected_timestamps is not None:
            # Caller pre-computed the expected trading-hour timestamps (e.g. DataBento
            # KLINE_1H uses EVENT_1H trading hours). Rows whose timestamps aren't in
            # this list are ignored; any trading hour absent from the data frame's
            # index marks the data as missing.
            if len(expected_timestamps) == 0:
                return False
            data_timestamps = set(data_frame.index.values.tolist())
            return any(ts not in data_timestamps for ts in expected_timestamps)
        period = data_type.get_period_in_mill()
        adjusted_start_time = int((start_time + period - 1) / period) * period
        adjusted_end_time = int(end_time / period) * period
        expected_length = int(
            (adjusted_end_time - adjusted_start_time) / period) + 1
        return expected_length != len(data_frame)

    @staticmethod
    def verify_update_status(all_updated: bool) -> bool:
        return all_updated

    @staticmethod
    def validate_data(full_symbol: str,
                      data_type: DataType,
                      hub_data: HubData,
                      config: Config):
        if config.missing_exception and hub_data.missing:
            raise DataError('{} of {}, data missing'.format(
                data_type.name, full_symbol))
        if config.updated_exception and not hub_data.updated:
            raise DataError('{} of {}, data download failed'.format(
                data_type.name, full_symbol))

    @staticmethod
    def validate_missing(symbol: str, data_type: DataType, s3_list: List[FileData],
                         center_list: List[ChunkData], missing_list: List[ChunkData], config: Config):
        if config.missing_exception:
            for item in s3_list:
                if item.data is None:
                    raise DataError('{} of {}, from {} to {}, data missing'.format(
                        data_type.name, symbol, item.start_time, item.end_time))

            for item in center_list:
                if item.data is None:
                    raise DataError('{} of {}, from {} to {}, data missing'.format(
                        data_type.name, symbol, item.start_time, item.end_time))

            if not DataValidator.is_gap_tolerant(symbol, data_type):
                for item in missing_list:
                    raise DataError('{} of {}, from {} to {}, data missing'.format(
                        data_type.name, symbol, item.start_time, item.end_time))
