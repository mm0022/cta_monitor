from abc import ABC, abstractmethod


class DownloadAdapter(ABC):
    @staticmethod
    def _parse_url(url: str):
        if '/' in url:
            return url.split('/', 1)
        raise Exception('invalid url')

    @abstractmethod
    def download(self, url: str, name: str, directory: str) -> str:
        pass
