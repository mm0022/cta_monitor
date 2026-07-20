import base64
import gzip
import hashlib
import json
import os
from decimal import Decimal
from io import StringIO
from os.path import abspath
from stat import S_IREAD, S_IRGRP, S_IROTH
from typing import TextIO, Tuple, List, Dict, Any
from uuid import uuid4

import pandas as pd
from pandas import DataFrame

from nexus_data_hub_sdk.exception.exceptions import FileOperationError
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.share.enums import DataType, FileType
from nexus_data_hub_sdk.share.settings import DECIMAL_STORAGE_TYPE
from nexus_data_hub_sdk.share.decorator import exception_wrapper


class FileHelper:
    K_LINE_COLUMNS = [
        ('start_time', int),
        ('open', DECIMAL_STORAGE_TYPE),
        ('high', DECIMAL_STORAGE_TYPE),
        ('low', DECIMAL_STORAGE_TYPE),
        ('close', DECIMAL_STORAGE_TYPE),
        ('volume', DECIMAL_STORAGE_TYPE),
        ('close_time', int),
        ('quoted_volume', DECIMAL_STORAGE_TYPE),
        ('trades', DECIMAL_STORAGE_TYPE),
        ('taker_buy_volume_in_base', DECIMAL_STORAGE_TYPE),
        ('taker_buy_volume_in_quoted', DECIMAL_STORAGE_TYPE),
        ('ignored', DECIMAL_STORAGE_TYPE)
    ]

    FUNDING_RATE_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('funding_time', int),
        ('funding_rate', DECIMAL_STORAGE_TYPE)
    ]

    INTEREST_RATE_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('interest_time', int),
        ('interest_rate', str)
    ]

    OPEN_INTEREST_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('open_interest_time', int),
        ('open_interest_rate', DECIMAL_STORAGE_TYPE)
    ]

    HAIRCUT_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sample_time', int),
        ('symbol', str),
        ('haircut', str),
        ('amt_in_usd', bool)
    ]

    HAIRCUT_DE_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sample_time', int),
        ('symbol', str),
        ('haircut_de', str),
        ('amt_in_usd', bool)
    ]

    PM_COLLATERAL_RATIO_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sample_time', int),
        ('symbol', str),
        ('pm_collateral_ratio', str),
        ('amt_in_usd', bool)
    ]

    MMR_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sample_time', int),
        ('symbol', str),
        ('mmr', str),
        ('amt_in_usd', bool)
    ]

    MMD_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sample_time', int),
        ('symbol', str),
        ('mmd', str),
        ('amt_in_usd', bool)
    ]

    STAKING_RATE_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('time', int),
        ('annual_percentage_rate', DECIMAL_STORAGE_TYPE),
        ('exchange_rate', DECIMAL_STORAGE_TYPE)
    ]

    INSURANCE_FUND_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('time', int),
        ('balance', DECIMAL_STORAGE_TYPE),
        ('asset', str)
    ]

    STREAMING_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('sequence_number', int),
        ('content_type', str),
        ('content', str),
    ]

    SEQUENCED_COLUMNS = [
        ('sequence_number', int),
        ('content_type', str),
        ('content', str),
    ]

    OPTIONS_25DELTA_SHEW_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('time', int),
        ('one_week_skew', DECIMAL_STORAGE_TYPE),
        ('one_month_skew', DECIMAL_STORAGE_TYPE),
        ('three_month_skew', DECIMAL_STORAGE_TYPE),
        ('six_month_skew', DECIMAL_STORAGE_TYPE),
    ]

    SINGLE_VALUE_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('t', int),
        ('v', DECIMAL_STORAGE_TYPE),
    ]

    STABLECOIN_SUPPLY_RATIO_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('t', int),
        ('h', DECIMAL_STORAGE_TYPE),
        ('l', DECIMAL_STORAGE_TYPE),
        ('v', DECIMAL_STORAGE_TYPE),
    ]

    MAP_DATA_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('t', int),
        ('o', str),
    ]

    EVENT_COLUMNS = [
        ('start_time', int),
        ('close_time', int),
        ('events', str),
    ]

    # This map indicating which data type's s3 file content should be normalized and the corresponding target col
    NEED_NORMALIZE_DATA_TYPES = {
        DataType.MMR: {
            "OKEXV5": "mmr"
        },
        DataType.PM_COLLATERAL_RATIO: {
            "BINANCE": "pm_collateral_ratio"
        }
    }

    @staticmethod
    def parse_dict(content: str) -> dict:
        parse_dict = json.loads(content)
        return {k: DECIMAL_STORAGE_TYPE(v) for k, v in parse_dict.items()}

    @staticmethod
    def generate_column_name(columns: List[Tuple]) -> List[str]:
        return [column[0] for column in columns]

    @staticmethod
    def generate_column_type(columns: List[Tuple]) -> Dict:
        return {column[0]: column[1] for column in columns}

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def checksum(file_path: str, checksum_type: str) -> str:
        if checksum_type == Constants.CHECKSUM_SHA256:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(Constants.FILE_CHUNK_SIZE), b""):
                    sha256_hash.update(chunk)
            return base64.b64encode(sha256_hash.digest()).decode('utf-8')
        raise Exception('Unsupported checksum type')

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def sha256(data: bytes) -> str:
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data)
        return base64.b64encode(sha256_hash.digest()).decode('utf-8')

    @staticmethod
    def read_csv_file_with_data_type(file: TextIO, data_type: DataType) -> DataFrame:
        if (data_type.is_kline_data()
                or data_type.is_index_price_data()
                or data_type.is_mark_price_data()
                or data_type.is_premium_index_data()):
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.K_LINE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.K_LINE_COLUMNS)
            )
        elif data_type.is_funding_rate_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.FUNDING_RATE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.FUNDING_RATE_COLUMNS)
            )
        elif data_type.is_interest_rate_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.INTEREST_RATE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.INTEREST_RATE_COLUMNS)
            )
            df['interest_rate'] = df['interest_rate'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_open_interest_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.OPEN_INTEREST_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.OPEN_INTEREST_COLUMNS)
            )
        elif data_type.is_haircut_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.HAIRCUT_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.HAIRCUT_COLUMNS)
            )
            df['haircut'] = df['haircut'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_haircut_de_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.HAIRCUT_DE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.HAIRCUT_DE_COLUMNS)
            )
            df['haircut_de'] = df['haircut_de'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_pm_collateral_ratio_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.PM_COLLATERAL_RATIO_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.PM_COLLATERAL_RATIO_COLUMNS)
            )
            df['pm_collateral_ratio'] = df['pm_collateral_ratio'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_mmr_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.MMR_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.MMR_COLUMNS)
            )
            df['mmr'] = df['mmr'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_mmd_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.MMD_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.MMD_COLUMNS)
            )
            df['mmd'] = df['mmd'].map(
                lambda c: json.loads(c, parse_float=Decimal))
        elif data_type.is_staking_rate_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.STAKING_RATE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.STAKING_RATE_COLUMNS)
            )
        elif data_type.is_insurance_fund_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.INSURANCE_FUND_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.INSURANCE_FUND_COLUMNS)
            )
        elif data_type.is_event_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.EVENT_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.EVENT_COLUMNS)
            )
            df['events'] = df['events'].map(lambda c: json.loads(c))
        elif data_type == DataType.STREAMING:
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.STREAMING_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.STREAMING_COLUMNS)
            )
        elif data_type == DataType.SEQUENCED:
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.SEQUENCED_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.STREAMING_COLUMNS)
            )
        elif data_type.is_options_25delta_skew_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.OPTIONS_25DELTA_SHEW_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.OPTIONS_25DELTA_SHEW_COLUMNS)
            )
        elif data_type.is_glass_node_single_value_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.SINGLE_VALUE_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.SINGLE_VALUE_COLUMNS)
            )
        elif data_type.is_glass_node_map_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.MAP_DATA_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.MAP_DATA_COLUMNS)
            )
            df['o'] = df['o'].map(
                lambda c: FileHelper.parse_dict(c))
        elif data_type.is_stablecoin_supply_ratio_data():
            df = pd.read_csv(
                file,
                header=None,
                names=FileHelper.generate_column_name(
                    FileHelper.STABLECOIN_SUPPLY_RATIO_COLUMNS),
                dtype=FileHelper.generate_column_type(
                    FileHelper.STABLECOIN_SUPPLY_RATIO_COLUMNS)
            )
        else:
            df = pd.read_csv(file, header=None, dtype=str)
        return df

    @staticmethod
    def normalize_file_number_to_decimal_if_needed(df: pd.DataFrame, exchange: str, data_type: DataType) -> pd.DataFrame:
        def convert_all_numbers_to_decimal(obj: Any) -> Any:
            if isinstance(obj, list):
                return [convert_all_numbers_to_decimal(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: convert_all_numbers_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, (int, float)):
                # str() preserves exact decimal representation
                return Decimal(str(obj))
            elif isinstance(obj, Decimal):
                return obj
            else:
                return obj
        target = FileHelper.NEED_NORMALIZE_DATA_TYPES.get(
            data_type, {}).get(exchange)

        if not target or target not in df.columns:
            return df
        df = df.copy()
        df[target] = df[target].apply(convert_all_numbers_to_decimal)
        return df

    @staticmethod
    def read_csv(data: bytes, file_type: FileType, data_type: DataType) -> DataFrame:
        if file_type == FileType.GZIP:
            decompressed_data = gzip.decompress(data)
        else:
            decompressed_data = data
        return FileHelper.read_csv_file_with_data_type(StringIO(decompressed_data.decode('utf-8')), data_type)

    @staticmethod
    def read_parquet(file_name: str) -> DataFrame:
        return pd.read_parquet(file_name)

    @staticmethod
    def write_parquet(data: DataFrame, file_name: str):
        FileHelper.remove_file(file_name)
        data.to_parquet(file_name, index=None, compression='snappy')
        os.chmod(file_name, S_IREAD | S_IRGRP | S_IROTH)

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def remove_file(file_name: str):
        if file_name and os.path.exists(file_name):
            os.remove(file_name)

    @staticmethod
    def set_index(data_frame: DataFrame, data_type: DataType):
        if data_type.is_market_data() or data_type == DataType.STREAMING:
            data_frame['index'] = data_frame['start_time']
            data_frame.set_index('index', drop=True, inplace=True)
        elif data_type == DataType.SEQUENCED:
            data_frame['index'] = data_frame['sequence_number']
            data_frame.set_index('index', drop=True, inplace=True)

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def move_file(src_file_name: str, desc_file_name: str):
        if src_file_name and desc_file_name and os.path.exists(src_file_name):
            os.chmod(src_file_name, S_IREAD | S_IRGRP | S_IROTH)
            os.rename(src_file_name, desc_file_name)

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def link_file(src_file_name: str, desc_file_name: str):
        if src_file_name and desc_file_name and os.path.exists(src_file_name):
            desc_temp_file_name = desc_file_name + '_' + str(uuid4())
            os.symlink(abspath(src_file_name), desc_temp_file_name)
            try:
                os.rename(desc_temp_file_name, desc_file_name)
            except FileExistsError:
                FileHelper.remove_file(desc_temp_file_name)

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def make_dir(name: str):
        if not os.path.exists(name):
            os.makedirs(name, exist_ok=True)

    @staticmethod
    @exception_wrapper(exception=FileOperationError)
    def validate_file_exists(name: str):
        if os.path.isfile(name):
            return
        raise Exception('File "{}" not exists'.format(name))
