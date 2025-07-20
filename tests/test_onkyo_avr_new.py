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
    response = '57'

    driver = driver_factory(response)
    result = {'output': response}
    driver.process_result('current_volume', config['commands']['current_volume'], result)
    assert result['result'] == 43.5


def test_execute(config, driver_factory):
    response = 'ISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1MVL57\x1a\r\n'

    driver = driver_factory(response)
    driver.connected = True
    driver.execute_command('set_volume', '43.5')
    message = struct.Struct(">4sIIB3x8s")
    driver.conn.send.assert_called_with(message.pack('ISCP'.encode(), 16, 8, 1, '!1MVL57\r'.encode()))


def test_long_response(config, driver_factory):

    response = 'ISCP\x00\x00\x00\x10\x00\x00\x00!\x01\x00\x00\x00!1NLTF3000000000E0000FFFF00NET\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x0b\x01\x00\x00\x00!1NLSC0P\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x11\x01\x00\x00\x00!1NLSU0-TuneIn\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x12\x01\x00\x00\x00!1NLSU1-Pandora\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x12\x01\x00\x00\x00!1NLSU2-Spotify\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x11\x01\x00\x00\x00!1NLSU3-Deezer\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x10\x01\x00\x00\x00!1NLSU4-Tidal\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x16\x01\x00\x00\x00!1NLSU5-AmazonMusic\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x1e\x01\x00\x00\x00!1NLSU6-Chromecast built-in\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x16\x01\x00\x00\x00!1NLSU7-DTS Play-Fi\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x12\x01\x00\x00\x00!1NLSU8-AirPlay\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x10\x01\x00\x00\x00!1NLSU9-Alexa\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x17\x01\x00\x00\x00!1NLSU0-Music Server\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x0e\x01\x00\x00\x00!1NLSU1-USB\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x0e\x01\x00\x00\x00!1NLSU2-USB\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\x15\x01\x00\x00\x00!1NLSU3-Play Queue\x1a\r\nISCP\x00\x00\x00\x10\x00\x00\x00\n\x01\x00\x00\x00!1AMT00\x1a\r\n'
    driver = driver_factory(response)
    driver.connected = True
    result = {'output': driver.send_command_raw('command1', config['commands']['command3'])}
    message = struct.Struct(">4sIIB3x10s")
    driver.conn.send.assert_called_with(message.pack('ISCP'.encode(), 16, 10, 1, '!1AMTQSTN\r'.encode()))
    driver.process_result('command2', config['commands']['command3'], result)
    assert result['result'] == 'off'
