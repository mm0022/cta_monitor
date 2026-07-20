# Data Hub SDK

The Python library for fetching data from Data Hub.

## Usage

### Install from the private repository.
The URL for the repository is https://pypi.cyberx-ops.com, the command to install the library would be: 
- **PIP**
```
pip install --index-url https://pypi.cyberx-ops.com/simple nexus-data-hub-sdk
```
We can add the private repository to the pip search index by creating the ```pip.conf``` (```pip.ini``` if on Windows) in any of the locations suggested by ```pip config -v list```, and then add the private repository index to ```pip.conf```.
```
[install]
extra-index-url = https://pypi.cyberx-ops.com/simple
``` 
Now, we can run ```pip install nexus-data-hub-sdk``` like the public PyPI repository.

- **Poetry**
We can add the dependency to the ```project.toml```.
```
[tool.poetry.dependencies]
nexus-data-hub-sdk = "^0.1.0"

[[tool.poetry.source]]
name = "nexus"
url = "https://pypi.cyberx-ops.com/simple"
secondary = true
```
And then run ```poetry update``` to update the dependencies.

### Use the library in the code

Using the ```Client``` class from the ```nexus-data-hub-sdk``` module:
```
from nexus_data_hub_sdk import Client, BusinessType, DataType, ExchangeType


client = Client('5aed5488fec148b291b0b90f2c701c1e', 
                missing_exception=True,
                updated_exception=False,
                http_download=True,
                download_concurrency=1,
                api_timeout=10.0,
                gateway_url='http://localhost:8085/nexus-data-hub-gateway',
                route_meta_rui='https://nexus-data-hub-default.s3.amazonaws.com/meta/route_meta.json')

data1 = client.request_by_type('BINANCE',
                              'SPOT',
                              'BTC_USDT',
                              DataType.KLINE_1M,
                              1694390400000,
                              end_time=1694491799999,
                              missing_exception=True,
                              updated_exception=False,
                              local_first=True)
                              
data2 = client2.request('BINANCE_SPOT_BTC_USDT.KLINE_1M',
                       1632392000000,
                       missing_exception=True,
                       updated_exception=False,
                       local_first=False)
                       
upload_result = client.file_upload('abc', 123, './.data/abc', 'parquet', delimiter='_', expiry_in=600)
with open('./.data/abc', 'rb') as f:
    data = f.read()
    upload_result = client.file_upload('abc', 123, data, 'parquet')

result = client.file_download('abc', 'parquet', 1, 123, 6, sort_direction='DESC')

client.streaming_commit('abc', 
                        '{"key": "value"}', 
                        66, 
                        'JSON', 
                        package_frequency='DAILY', 
                        start_time=1697726075000, 
                        end_time=1697726076000)
client.streaming_commit('abc', '123,"a,b,c",456,xyz', 88, 'CSV')

streaming_data = client.request_streaming_data('abc', 1697726075000, end_time=1697726076000, updated_exception=False)

set_result = client.kv_set('test_key', '{"key1":"value", "key2":123}', 60)

get_result = client.kv_get('test_key')

resp = client.sequenced_commit('ABC', ['{"key": "value"'], 'JSON', pre_seq_number=188)

sequenced_data = client.request_sequenced_data('ABC', 1, end_sequence_number=100, updated_exception=False)

sequenced_data = client.request_latest_sequenced_data('ABC', limit=100, updated_exception=False)

kline_generator = client.request_kline_detail(exchange='BINANCE', business='SPOT', category='KLINE*', sym='BTC_USDT')
for items in kline_generator:
    pass

streaming_generator = client.request_streaming_detail(key='ABC')
for items in streaming_generator:
    pass

sequenced_generator = client.request_sequenced_detail(key='ABC')
for items in sequenced_generator:
    pass

notebook_generator = client.request_notebook_detail(key='ABC')
for items in notebook_generator:
    pass
    
streaming_keys = client.request_streaming_key_by_limit(key_prefix='PROD', start_key='PROD_KEY', included=false, limit=200)

streaming_detail = client.request_streaming_detail_by_key(streaming_keys)

sequenced_keys = client.request_sequenced_key_by_limit(key_prefix='PROD', start_key='PROD_KEY', included=false, limit=200)

sequenced_detail = client.request_sequenced_detail_by_key(sequenced_keys)

meta_symbol_list = client.get_meta_symbols(['BINANCE_SPOT_BTC_USDT'])
```
For the constructor of the Client class:
- `5aed5488fec148b291b0b90f2c701c1e` (str): The API key for requests to the data hub.
- `missing_exception` (bool): If `True`, raise DataError exception when any data is missing. If `False`, disables the feature. Default is `True`.
- `updated_exception` (bool): If `True`, raise DataError exception when any data isn't updated from the data hub. If `False`, disables the feature. Default is `True`.
- `http_download` (bool): If `True`, use httpx to download files from S3. If `False`, use boto3 to download files from S3. Default is `True`.
- `download_concurrency` (int): The number of concurrent threads to download files, Default is the number of CPUs.
- `api_timeout` (float): The timeout for http request, Default is 30 seconds.
- `gateway_url` (str): The url of the data hub gateway. Default is the value of `DATA_HUB_GATEWAY_URL` env.
- `route_meta_uri` (str): The uri of the route meta file on S3. Default is the combination of `ROUTE_META_BUCKET` and `ROUTE_META_KEY` envs.

For the request_by_type method:
- `BINANCE` (str): The requested exchange type.
- `SPOT` (str): The requested business type.
- `BTC_USDT` (str): The requested currency symbol.
- `DataType.KLINE_1M` (DataType): The requested data type.
- `1694390400000` (int): The requested start timestamp.
- `end_time` (int): The requested end timestamp, the default value is 9999999999999.
- `missing_exception` (bool) and `updated_exception` (bool): These parameters will re-write the constructor's parameters.
- `local_first` (bool): If `True`, request data from the local cache first. If there is missing data from the requested data, the data hub will be requested. If `False`, request from the data hub. Default is `False`.

For the request method:
- `BINANCE_SPOT_BTC_USDT.KLINE_1M` (str): The requested symbol. The format is "EXCHANGE_BUSINESS_CURRENCY1_CURRENCY2.DATATYPE".
- `1694390400000` (int): The requested start timestamp.
- `end_time` (int): The requested end timestamp, the default value is 9999999999999.
- `missing_exception` (bool) and `updated_exception` (bool): These parameters will re-write the constructor's parameters.
- `local_first` (bool): If `True`, request data from the local cache first. If there is missing data from the requested data, the data hub will be requested. If `False`, request from the data hub. Default is `False`.

For the file_upload method:
- `abc` (str): The key of the file.
- `123` (int): The version of the file.
- `./.data/abc` (str) or `data` (bytes): The file name with the directory or the content of the file.
- `parquet` (str): The type of the file.
- `delimiter` (str): The delimiter of the key, the default value is "_".
- `expiry_in` (int): The expiry of the index in second. Default value is 'None'.

For the file_download method:
- `abc` (str): The key of the file.
- `parquet` (str): The type of the file.
- `1` (int): The lower version of the file.
- `123` (int): The upper version of the file.
- `6` (int): The number of the return files.
- `sort_direction` (str): The select direction of notebooks, the default value is DESC.

For the streaming_commit method:
- `abc` (str): The key of the streaming data.
- `{"key1": "value"}` (str): The content of the streaming data.
- `66` (int): The sequence number of the streaming data.
- `JSON` (str): The type of the content.
- `DAILY` (str): The packaging frequency of the streaming data, the default value is "DAILY", accepted value is "HOURLY", "DAILY" and "MONTHLY".
- `1697726075000` (int): The start time of the streaming data. Default value is 'None' and the current timestamp will be assigned to this field.
- `1697726076000` (int): The end time of the streaming data. Default value is 'None' and the start time will be assigned to this field.

For the request_streaming_data method:
- `abc` (str): The key of the streaming data.
- `1697726075000` (int): The requested start timestamp.
- `1697726076000` (int): The requested end timestamp, the default value is 9999999999999.
- `updated_exception` (bool): These parameters will re-write the constructor's parameters.

For the kv_set method:
- `key` (str): The key of the cache data.
- `value` (str): The value of the cache data.
- `ttl` (int): The time to live of the cache data.

For the kv_get method:
- `key` (str): The key of the cache data.

For the sequenced_commit method:
- `ABC` (str): The key of the sequenced data.
- `['{"key": "value"}']` (List[str]): The list of the streaming records.
- `JSON` (str): The type of the content.
- `188` (int): The sequence number of the record that this record is based on.

For the request_sequenced_data method:
- `ABC` (str): The key of the sequenced data.
- `1` (int): The requested start sequence number.
- `100` (int): The requested end sequence number, the default value is 9223372036854775807.
- `updated_exception` (bool): These parameters will re-write the constructor's parameters.

For the request_latest_sequenced_data method:
- `ABC` (str): The key of the sequenced data.
- `100` (int): The number of records in desc order, the default value is 1.
- `updated_exception` (bool): These parameters will re-write the constructor's parameters.

For the request_kline_detail method:
- `BINANCE` (str): The exchange name. Default is None.
- `SPOT` (str): The business type. Default is None.
- `KLINE_1M` (str): The data type. Default is None.
- `BTC_USDT` (str): The symbol name. Default is None.
exchange, business, category and sym should be assigned or not together, or method will request all kinds of kline.

For the request_streaming_detail method:
- `ABC` (str): The key. Default is None.
If key parameter is not provided, all streaming data detail will be return.

For the request_sequenced_detail method:
- `ABC` (str): The key. Default is None.
If key parameter is not provided, all sequenced data detail will be return.

For the request_notebook_detail method:
- `ABC` (str): The key. Default is None.
If key parameter is not provided, all notebook data detail will be return.

For the request_streaming_key_by_limit and request_sequenced_key_by_limit methods:
- `PROD` (str): The prefix of the keys that does not contain '*'. Default is None.
- `PROD` (str): The start key of the range.
- `false` (bool): If the start key is included in the range.
- `200` (int): The max number of keys . Default is 100.

For the request_streaming_detail_by_key and request_sequenced_detail_by_key method:
- `streaming_keys` or `sequenced_keys` (List(str)): The list of keys to get detail data.

For the get_meta_symbols method:
- `['BINANCE_SPOT_BTC_USDT']` (List[str]): The list of the symbols required.

The request, request_by_type request_streaming_data and request_sequenced_data methods return a DataFrame object, which is a subclass of pydantic BaseModel:
```
class HubData(BaseModel):
    missing: bool
    updated: bool
    data: DataFrame
```
- `missing` (bool): If `True`, there is some data missing. If `False`, all data is returned.
- `updated` (bool): If `True`, all data is download correctly. If `False`, there is some data failed to download from the data hub.
- `data` (pandas.DataFrame): The requested data.

The file_upload and file_download methods return a notebook or a list of notebook, which is a subclass of pydantic BaseModel:
```
class Notebook(SDKBaseModel):
    key: str
    version: int
    url: str
    fingerprint_algorithm: str
    fingerprint: str
    file_type: str
    file_name: str
    file_path: Optional[str]
```
- `key` (str): The key of the file.
- `version` (int): The version of the file.
- `url` (str): The S3 address of the file.
- `fingerprint_algorithm` (str): The hash algorithm to generate the fingerprint.
- `finger_print` (str): The fingerprint of the file.
- `file_type` (str): The type of the file.
- `file_name` (str): The name of the file.
- `file_paht` (str): The path of the file where it is downloaded.

The kv_set and kv_get methods return a CacheResponse object:
```
class CacheResponse(SDKBaseModel):
    key: str
    value: str
```
- `key` (str): The key of the cache data to set or get.
- `value` (str): For set method, value is `OK` to indicate the result of the method. For get method, value is the value of the requested key.

The sequenced_commit method returns a list of SequencedData objects:
```
class SequencedData(SDKBaseModel):
    key: str
    content: str
    content_type: str
    seq_number: int
```
- `key` (str): The key of the record.
- `content` (str): The content of the record.
- `content_type` (str): The content type of the record.
- `seq_number` (int): The sequence number of the record.

The request_kline_detail, request_streaming_detail, request_sequenced_detail and request_notebook_detail methods return a generator of detail data, you can iterate the generator to get all the returns.
```
for items in sequenced_generator:
    pass
```
The `items` is a list of detail data of `KlineDetail`, `StreamingAndSequencedBaseDetail` or `NotebookDetail` objects: 
The request_streaming_detail_by_key and request_sequenced_detail_by_key method return a list of `StreamingAndSequencedBaseDetail` objects.
```
class ChunkDetail(SDKBaseModel):
    start: int
    end: int
    missing: bool
    confidence: int
    
    
class KlineDetail(SDKBaseModel):
    exchange: str
    business: str
    category: str
    sym: str
    start: int
    end: int
    chunks: List[ChunkDetail]


class StreamingAndSequencedBaseDetail(SDKBaseModel):
    key: str
    packagePosition: int
    start: int
    end: int


class StreamingAndSequencedDetail(StreamingAndSequencedBaseDetail):
    frequency: str
    createdAt: int
    updatedAt: int


class NotebookDetail(SDKBaseModel):
    key: str
    fileType: str
    minVersion: int
    maxVersion: int
    count: int
```

The SDK might raise ParamInvalidError, FileOperationError, DownloadError, NexusHubAPIError, DataError and SetupError, which are inherited from SDKError.


## Build Package

To build the Python library, we need ```GNU make```.
```
# OSX
brew install make
# Debian
apt install make
# RHEL
yum install make
```
And then,  at the root directory of the project:
```
make build
```

## Release to CyberX PyPi repository

### Manual release
We must configure the credentials before uploading the package to the repository, or you will be prompted to enter them when performing the release action.
```
export POETRY_HTTP_BASIC_CYBERX_USERNAME=username
export POETRY_HTTP_BASIC_CYBERX_PASSWORD=password
```
 And then, at the root directory of the project:
```
make release
```

### CI releases
When a new commit is pushed to the master, dev, or dev-* branches, the `GitHub action` will automatically build and deploy the package to the repo.

Ensure that the version number in `pyproject.toml` is correctly maintained.

We can use the bump-version.sh script in the bin directory to assign a new version number to the project.

### Maintenance

To Format Code
```shell
# ensure that GNU make was installed in advance
make fmt
```
