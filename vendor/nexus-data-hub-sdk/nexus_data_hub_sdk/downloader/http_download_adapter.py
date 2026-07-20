import os
import uuid

import httpx

from nexus_data_hub_sdk.downloader.download_adapter import DownloadAdapter
from nexus_data_hub_sdk.util.file_helper import FileHelper
from nexus_data_hub_sdk.share.constants import Constants


class HttpDownloadAdapter(DownloadAdapter):
    def download(self, url: str, name: str, directory: str) -> str:
        bucket, key = self._parse_url(url)
        local_name = os.path.join(directory, name)
        http_url = self.__generate_download_url(bucket, key)
        self.__download(http_url, local_name)
        return local_name

    @staticmethod
    def __generate_download_url(bucket: str, key: str) -> str:
        return 'https://{}.s3.amazonaws.com/{}'.format(bucket, key)

    def __download(self, url: str, file_path_name: str):
        temp_name = file_path_name + '-' + str(uuid.uuid4())
        retry = self.__retry
        while retry > 0:
            try:
                with self.__http_client.stream('GET', url) as response:
                    if response.status_code == 200:
                        with open(temp_name, 'wb') as out_file:
                            for chunk in response.iter_bytes(chunk_size=self.__chunk_size):
                                out_file.write(chunk)
                    else:
                        raise Exception(
                            'Bad status code: {}'.format(response.status_code))
                FileHelper.move_file(temp_name, file_path_name)
                return
            except Exception as e:
                retry = retry - 1
                if retry <= 0:
                    raise Exception(
                        'Failed to download from {}, {}'.format(url, str(e)))
            finally:
                FileHelper.remove_file(temp_name)

    def __init__(self, retry: int = 5, timeout: float = 5.0):
        self.__retry = retry
        self.__chunk_size = 5 * Constants.FILE_CHUNK_SIZE
        self.__http_client = httpx.Client(http2=True, timeout=timeout)
