from typing import List

from nexus_data_hub_sdk.exception.exceptions import DownloadError
from nexus_data_hub_sdk.downloader.download_adapter import DownloadAdapter
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.share.enums import DataType, FileType
from nexus_data_hub_sdk.share.executor import Executor
from nexus_data_hub_sdk.util.file_helper import FileHelper
from nexus_data_hub_sdk.share.decorator import exception_wrapper
from nexus_data_hub_sdk.share.logger import logger


class DownloadTask:
    def __init__(self,
                 url: str,
                 file_name: str,
                 file_type: FileType,
                 finger_print: str,
                 data_type: DataType):
        self.url = url
        self.file_name = file_name
        self.file_type = file_type
        self.finger_print = finger_print
        self.downloaded = False
        self.data_type = data_type


class Downloader:
    def __init__(self, adapter: DownloadAdapter, directory: str, retry: int = 0, thread: int = Constants.MAX_THREAD):
        self.__adapter = adapter
        self.__directory = directory
        self.__retry = retry
        self.__thread = thread
        FileHelper.make_dir(directory)

    def __download_file(self, task: DownloadTask):
        temp_file_name_with_directory = None
        try:
            parts = task.url.split('//', 1)
            url = parts[1] if len(parts) > 1 else parts[0]
            temp_file_name = task.file_name + '.tmp'
            temp_file_name_with_directory = self.__adapter.download(
                url, temp_file_name, self.__directory)
            self.__check_fingerprint(task.finger_print,
                                     temp_file_name,
                                     temp_file_name_with_directory,
                                     url)
            if (task.data_type.is_market_data()
                    or task.data_type == DataType.STREAMING
                    or task.data_type == DataType.SEQUENCED):
                with open(temp_file_name_with_directory, 'rb') as f:
                    data = f.read()

                df = FileHelper.normalize_file_number_to_decimal_if_needed(df=FileHelper.read_csv(
                    data, task.file_type, task.data_type), exchange=url.split("/")[1], data_type=task.data_type)

                FileHelper.write_parquet(
                    df, temp_file_name_with_directory.rpartition('.')[0])
            else:
                FileHelper.move_file(
                    temp_file_name_with_directory, temp_file_name_with_directory.rpartition('.')[0])
            task.downloaded = True
        except Exception as e:
            logger.error('Failed to download file from {}'.format(task.url))
            raise e
        finally:
            FileHelper.remove_file(temp_file_name_with_directory)

    def __check_fingerprint(self,
                            fingerprint: str,
                            file_name: str,
                            file_name_with_directory: str,
                            url: str):
        retry_count = self.__retry
        while retry_count >= 0:
            if fingerprint != FileHelper.checksum(file_name_with_directory, Constants.CHECKSUM_SHA256):
                FileHelper.remove_file(file_name_with_directory)
                if retry_count > 0:
                    retry_count = retry_count - 1
                    self.__adapter.download(url, file_name, self.__directory)
                else:
                    raise Exception(
                        'Fingerprint mismatched for s3://{}'.format(url))
            else:
                return

    @exception_wrapper(exception=DownloadError)
    def download_files(self, tasks: List[DownloadTask], concurrency: int):
        if tasks:
            Executor.submit(self.__download_file, tasks,
                            concurrency=concurrency)
