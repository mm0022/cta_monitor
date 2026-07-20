# import string
# import random
#
# from nexus_data_hub_sdk import DataType
# from nexus_data_hub_sdk.exception.exceptions import SDKError
# from nexus_data_hub_sdk.client.nexus_hub_client import Client
#
#
# class TestClient:
#     @staticmethod
#     def random_string(length):
#         letters = string.ascii_letters + string.digits
#         return ''.join(random.choice(letters) for i in range(length))
#
#     def upload(self, client):
#         client.file_upload(self.random_string(
#             10), 123, './.data/abc', 'parquet', expiry_in=600)
#
#     def test_request(self):
#         # client = Client('https://nexus.cyberx.cc/',
#         #                 missing_exception=True,
#         #                 updated_exception=False)
#
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e',
#                             # gateway_url='http://localhost:8085/nexus-data-hub-gateway/',
#                             # route_meta_uri='nexus-data-hub-default/meta/route_meta.json',
#                             missing_exception=False,
#                             updated_exception=False,
#                             local_first=False)
#
#             # data1 = client.request_by_type('BINANCE',
#             #                                'SPOT',
#             #                                'ETH_USDT',
#             #                                DataType.KLINE_1M,
#             #                                1696291200000,
#             #                                1696377599999,
#             #                                local_only=True)
#             data2 = client.request(
#                 'DATABENTO_FUT_NQ_V0.KLINE_1H', 1641164400000, 1778803200000)
#             # data3 = client.request_by_type('BINANCE',
#             #                                'SPOT',
#             #                                'BTC_USDT', DataType.KLINE_1M,
#             #                                1675123456789,
#             #                                missing_exception=True)
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_upload_download(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e',
#                             missing_exception=False,
#                             updated_exception=False)
#             # Executor.submit(self.upload, [client for _ in range(1)])
#
#             # with open('./.data/abc', 'rb') as f:
#             #     data = f.read()
#             #     upload_result = client.file_upload('abc', 127, data,
#             #                                        'parquet', expiry_in=600)
#             # upload_result = client.file_upload('TEST-XYZ', 130, './.data/abc',
#             #                                    'text', expiry_in=6000)
#             result = client.file_download(
#                 'CYBERX_DEV-FUNDING-MMR_HAIRCUT-BYBIT', 'parquet', limit=1)
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_streaming_data(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e',
#                             missing_exception=False,
#                             updated_exception=False)
#             client.streaming_commit('TEST-ABC', '{"key": "value"}', 2, 'JSON')
#             # client.streaming_commit('abc', 'test', 667, 'CSV')
#             result = client.request_streaming_data('TEST-ABC', 1699567622571)
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_cache_data(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e')
#             set_result = client.kv_set(
#                 'TEST-ABC', '{"key":"value", "number":123"}')
#             get_result = client.kv_get('TEST-ABC')
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_meta_sync(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e',
#                             gateway_url='http://localhost:8085/nexus-data-hub-gateway/',
#                             route_meta_uri='nexus-data-hub-default/meta/route_meta.json',
#                             )
#             result = client.get_meta_symbols(['BINANCE_PERP_1000PEPE_USDT'])
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_sequenced_streaming_data(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e')
#             # resp = client.sequenced_commit('TEST-ABC', ['{"key107": "value107"}'], 'JSON')
#             result = client.request_sequenced_data('TEST-ABC', 1)
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_latest_sequenced(self):
#         try:
#             client = Client('2bbf5f22a89f40f0bc8f78c8503e61e9')
#             # resp = client.sequenced_commit(
#             #     'TEST-ABC', ['{"a": 1}', '{"b": 2}'], 'json')
#             result = client.request_latest_sequenced_data(
#                 'CYBERX_STAGING_BINANCE_SPOT_TRADE_ETH_USDT', 400)
#         except SDKError as e:
#             print(e)
#         del client
#
#     def test_details(self):
#         try:
#             client = Client('5aed5488fec148b291b0b90f2c701c1e')
#             generator = client.request_kline_detail()
#             for item in generator:
#                 pass
#             generator = client.request_streaming_detail()
#             for item in generator:
#                 pass
#             generator = client.request_sequenced_detail()
#             for item in generator:
#                 pass
#             generator = client.request_notebook_detail()
#             for item in generator:
#                 pass
#             keys = client.request_sequenced_key_by_limit(key_prefix='TEST')
#             detail = client.request_sequenced_detail_by_key(keys)
#         except SDKError as e:
#             print(e)
#         del client
