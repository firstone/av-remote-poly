import pytest
import yaml


@pytest.fixture(scope='session')
def config_data():
    with open('tests/config.yaml', 'r') as configFile:
        return yaml.safe_load(configFile)
