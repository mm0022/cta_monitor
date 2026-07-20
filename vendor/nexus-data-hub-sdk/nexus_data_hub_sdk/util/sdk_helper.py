from io import StringIO
from typing import List

from pandas import DataFrame

from nexus_data_hub_sdk.share.enums import DataType
from nexus_data_hub_sdk.util.file_helper import FileHelper


class SdkHelper:
    @staticmethod
    def parse_data(data: List[str], dt: DataType) -> DataFrame:
        with StringIO('\n'.join(data)) as text_file:
            df = FileHelper.read_csv_file_with_data_type(text_file, dt)
            FileHelper.set_index(df, dt)
            return df
