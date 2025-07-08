import pytest
import struct
from unittest.mock import Mock
import yaml

from drivers.onkyo_avr_new import OnkyoAVRNew


@pytest.fixture
def config(config_data):
    return config_data['onkyo']


@pytest.fixture
def driver_factory(config):

    def inner(response=None):
        driver = OnkyoAVRNew(None, config, Mock())
        driver.conn = Mock()
        driver.conn.recv = Mock(return_value=(response.encode() if response is not None else None))

        return driver

    return inner


def test_simple(config, driver_factory):
    response = 'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1MVL57\x1a\r\n'

    driver = driver_factory(response)
    driver.connected = True
    driver.send_command_raw('set_volume', config['commands']['set_volume'], '43.5')
    message = struct.Struct(">4sIIB3x8s")
    driver.conn.send.assert_called_with(message.pack('ISCP'.encode(), 16, 8, 1, '!1MVL57\r'.encode()))


def test_output(config, driver_factory):
    response = 'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1MVL57\x1a\r\n'

    driver = driver_factory(response)
    result = {'output': response}
    driver.process_result('current_volume', config['commands']['current_volume'], result)
    assert result['result'] == 43.5
