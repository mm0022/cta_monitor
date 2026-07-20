class SDKError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ParamInvalidError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)


class FileOperationError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)


class NexusHubAPIError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)


class DataError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)


class SetupError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)


class DownloadError(SDKError):
    def __init__(self, message: str):
        super().__init__(message)
