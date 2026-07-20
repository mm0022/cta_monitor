import os
from pytest import fixture


@fixture
def cache_dir():
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    return current_dir + '/.data'


@fixture
def fixture_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
