import moto

from nexus_data_hub_sdk.util.file_helper import FileHelper


def test_file_hash(fixture_dir):
    with moto.mock_s3():
        with open(fixture_dir + '/ADAUSDT-1m-2023-08-01.csv', 'rb') as f:
            sha256 = FileHelper.sha256(f.read())
            assert sha256 == '2d25508d35da8bf280c7a1f97c2cceee55b60a1d2300fd7a3eb5e4b5ec8df90e'
