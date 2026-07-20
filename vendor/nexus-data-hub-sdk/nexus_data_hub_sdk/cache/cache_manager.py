import json
import os
from collections import defaultdict
from threading import RLock
from typing import Dict, List, Optional, Final

from portalocker import portalocker

from nexus_data_hub_sdk.downloader.downloader import DownloadTask
from nexus_data_hub_sdk.exception.exceptions import FileOperationError
from nexus_data_hub_sdk.share.constants import Constants
from nexus_data_hub_sdk.share.custom_encoder import CustomEncoder
from nexus_data_hub_sdk.share.decorator import exception_wrapper
from nexus_data_hub_sdk.share.enums import DataType
from nexus_data_hub_sdk.share.executor import Executor
from nexus_data_hub_sdk.share.models import FileMeta, ChunkData, FileData
from nexus_data_hub_sdk.util.file_helper import FileHelper


class CacheManager:
    @exception_wrapper(exception=FileOperationError)
    def __init__(self, directory: str):
        self.__directory: Final = directory
        FileHelper.make_dir(self.__directory)

    def __enter__(self):
        file_name = os.path.join(self.__directory, Constants.MEAT_FILE_NAME)
        if os.path.exists(file_name):
            self.__file = open(file_name, 'rt+')
        else:
            try:
                self.__file = open(file_name, 'xt+')
            except FileExistsError:
                self.__file = open(file_name, 'rt+')
        portalocker.lock(self.__file, portalocker.LockFlags.EXCLUSIVE)
        self.__data = self.__nested_dict()
        if os.stat(file_name).st_size != 0:
            self.__load_meta_data()
        self.__cache_lock = RLock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        has_file = hasattr(self, '_CacheManager__file') and self.__file
        if self.__data and has_file:
            self.save_to_file()
        if has_file:
            self.__file.close()

    @exception_wrapper(exception=FileOperationError)
    def __load_meta_data(self):
        self.__file.seek(0)
        data = json.load(self.__file)
        for item in data:
            meta = FileMeta.from_dict(item)
            self.__add(meta)

    def __add(self, meta: FileMeta):
        self.__data[meta.exchange_type][meta.data_type.name][meta.business_type][
            meta.symbol][meta.start_time] = meta

    def __get_duplicate(self, meta: FileMeta) -> List[FileMeta]:
        ret = list()
        index = self.__data.get(meta.exchange_type, {}).get(
            meta.data_type.name, {}).get(meta.business_type, {}).get(meta.symbol, {})
        for v in index.values():
            if meta.start_time <= v.start_time and v.end_time <= meta.end_time:
                ret.append(v)
        return ret

    def get_file_list(self, data: FileData) -> List[FileData]:
        meta_list = self.__get_duplicate(data)
        return [FileData(**f.to_dict()) for f in meta_list]

    def __remove_duplicate(self, meta: FileMeta) -> List[FileMeta]:
        ret = list()
        index = self.__data.get(meta.exchange_type, {}).get(
            meta.data_type.name, {}).get(meta.business_type, {}).get(meta.symbol, {})
        for v in index.values():
            if meta.start_time <= v.start_time and v.end_time <= meta.end_time:
                if meta.start_time != v.start_time or meta.end_time != v.end_time:
                    ret.append(v)
        for f in ret:
            del index[f.start_time]
        return ret

    @exception_wrapper(exception=FileOperationError)
    def save_to_file(self):
        with self.__cache_lock:
            self.__file.seek(0)
            data = list()
            self.__transform(self.__data, data)
            self.__file.write(json.dumps(data, cls=CustomEncoder, indent=2))
            self.__file.truncate()

    @staticmethod
    def __transform(source: Dict | List | FileMeta, target: List[FileMeta]):
        for v in source.values():
            if isinstance(v, FileMeta):
                target.append(v)
            elif isinstance(v, List):
                for item in v:
                    CacheManager.__transform(item, target)
            else:
                CacheManager.__transform(v, target)

    def generate_download_list(self, meta_list: List[FileMeta]) -> List[DownloadTask]:
        # Return the file list to download, if the file mate is not in the lookup table or the fingerprint is different
        with self.__cache_lock:
            ret = list()
            for v in meta_list:
                if not self.__find_file_meta_with_fingerprint(v):
                    ret.append(DownloadTask(url=v.url, file_name=v.file_name, file_type=v.file_type,
                                            finger_print=v.finger_print, data_type=v.data_type))
                elif not os.path.exists(os.path.join(self.__directory, v.file_name)):
                    self.remove(v)
                    ret.append(DownloadTask(url=v.url, file_name=v.file_name, file_type=v.file_type,
                                            finger_print=v.finger_print, data_type=v.data_type))
            return ret

    def __find_file_meta(self, meta: FileMeta) -> Optional[FileMeta]:
        # To find the meta in the lookup table, which has the same fingerprint with the input
        return self.__data.get(meta.exchange_type, {}).get(meta.data_type.name, {}).get(
            meta.business_type, {}).get(meta.symbol, {}).get(meta.start_time)

    def __find_file_meta_with_fingerprint(self, meta: FileMeta) -> Optional[FileMeta]:
        # To find the meta in the lookup table, which has the same fingerprint with the input
        index = self.__data.get(meta.exchange_type, {}).get(meta.data_type.name, {}).get(
            meta.business_type, {}).get(meta.symbol, {}).get(meta.start_time)
        if index and meta.finger_print == index.finger_print:
            return index
        return None

    def update(self, files: List[FileMeta]):
        with self.__cache_lock:
            expired_list = list()
            for f in files:
                if f.updated:
                    expired_list.extend(self.__remove_duplicate(f))
                    if not any(m for m in expired_list if m.start_time == f.start_time and m.end_time == f.end_time):
                        self.__add(f)
                elif self.__find_file_meta(f):
                    duplicate_list = self.__get_duplicate(f)
                    for d in duplicate_list:
                        d.updated = False
            self.save_to_file()
            Executor.map(self.__delete_file, expired_list)

    def get_directory(self) -> str:
        return self.__directory

    def get_meta_list_from_cache(self, exchange_type: str, data_type: DataType, business_type: str, symbol: str) -> List[FileMeta]:
        meta_map = self.__data.get(exchange_type, {}).get(
            data_type.name, {}).get(business_type, {}).get(symbol, {})
        return list(meta_map.values())

    def __nested_dict(self):
        return defaultdict(self.__nested_dict)

    def __delete_file(self, file: FileMeta):
        name = os.path.join(self.__directory, file.file_name)
        FileHelper.remove_file(name)

    def get_meta_list(self,
                      symbol: str,
                      business_type: str,
                      start_time: int,
                      end_time: int,
                      data_type: DataType,
                      exchange_type: str) -> (List[FileMeta], List[ChunkData], List[ChunkData]):
        with self.__cache_lock:
            s3_list = list()
            center_list = list()
            missing_list = list()
            meta_map = self.__data.get(exchange_type, {}).get(
                data_type.name, {}).get(business_type, {}).get(symbol, {})
            for meta in meta_map.values():
                if max(start_time, meta.start_time) <= min(end_time, meta.end_time):
                    s3_list.append(meta)
            s3_list.sort(key=lambda x: x.start_time)

            for i in range(len(s3_list)):
                if i == 0:
                    if start_time < s3_list[i].start_time:
                        missing_list.append(
                            ChunkData(start_time=start_time, end_time=s3_list[i].start_time - 1, missing=True))
                elif i == len(s3_list) - 1:
                    if s3_list[i].end_time < end_time:
                        missing_list.append(
                            ChunkData(start_time=s3_list[i].end_time + 1, end_time=end_time, missing=True))
                else:
                    if s3_list[i - 1].end_time + 1 < s3_list[i].start_time:
                        missing_list.append(ChunkData(
                            start_time=s3_list[i - 1].end_time + 1, end_time=s3_list[i].start_time - 1, missing=True))

            return s3_list, center_list, missing_list

    def remove(self, file_meta: FileMeta):
        with self.__cache_lock:
            index = self.__data.get(file_meta.exchange_type, {}).get(file_meta.data_type.name, {
            }).get(file_meta.business_type, {}).get(file_meta.symbol, {})
            if index.get(file_meta.start_time, None) is not None:
                del index[file_meta.start_time]
            self.save_to_file()
