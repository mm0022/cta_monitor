__docformat__ = 'restructuredtext'

# Check the dependencies
dependencies = ['boto3', 'psutil', 'pydantic',
                'portalocker', 'pandas', 'pyarrow', 'httpx', 'tomli']

missing_dependencies = []

for dependency in dependencies:
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.append(f"{dependency}: {e}")

if missing_dependencies:
    raise ImportError(
        "Unable to import required dependencies:\n" +
        "\n".join(missing_dependencies)
    )
del dependencies, dependency, missing_dependencies


from nexus_data_hub_sdk.client.nexus_hub_client import Client  # noqa: E402
from nexus_data_hub_sdk.client.hub_data import HubData, Notebook  # noqa: E402
from nexus_data_hub_sdk.share.enums import DataType  # noqa: E402
from nexus_data_hub_sdk.exception.exceptions import SDKError, ParamInvalidError, FileOperationError, NexusHubAPIError, DataError, SetupError, DownloadError  # noqa: E402
from nexus_data_hub_sdk.share.models import CacheResponse  # noqa: E402
