class Config:
    def __init__(self,
                 missing_exception: bool,
                 updated_exception: bool,
                 http_download: bool,
                 download_concurrency: int,
                 api_timeout: float,
                 local_first: bool):
        self.missing_exception = missing_exception
        self.updated_exception = updated_exception
        self.http_download = http_download
        self.download_concurrency = download_concurrency
        self.api_timeout = api_timeout
        self.local_first = local_first
