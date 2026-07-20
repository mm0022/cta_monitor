import concurrent.futures
from typing import List, Callable

from nexus_data_hub_sdk.share.constants import Constants


class Executor:
    @staticmethod
    def submit(fn: Callable, params: List, concurrency: int = Constants.MAX_THREAD) -> List:
        if concurrency <= 0:
            concurrency = 1
        with concurrent.futures.ThreadPoolExecutor(concurrency) as executor:
            futures = [executor.submit(fn, p) for p in params]
        return [f.result() for f in futures]

    @staticmethod
    def map(fn: Callable, params: List, concurrency: int = Constants.MAX_THREAD):
        if concurrency <= 0:
            concurrency = 1
        with concurrent.futures.ThreadPoolExecutor(concurrency) as executor:
            executor.map(fn, params)
