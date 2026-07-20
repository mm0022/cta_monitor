import os

import boto3
from boto3.s3.transfer import TransferConfig
from botocore import UNSIGNED
from botocore.config import Config

from nexus_data_hub_sdk.downloader.download_adapter import DownloadAdapter


class S3DownloadAdapter(DownloadAdapter):
    def __init__(self):
        self.__s3_client = boto3.client(
            's3', config=Config(signature_version=UNSIGNED))
        self.__download_config = TransferConfig(use_threads=False)

    def download(self, url: str, name: str, directory: str) -> str:
        bucket, key = self._parse_url(url)
        local_name = os.path.join(directory, name)
        self.__s3_client.download_file(
            bucket, key, local_name, Config=self.__download_config)
        return local_name
