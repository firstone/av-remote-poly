import pytest
from unittest.mock import Mock

from drivers.denon_avr import DenonAVR


@pytest.fixture(scope='session')
def config(config_data):
    return config_data['denon']


@pytest.fixture
def driver(config):
    driver = DenonAVR(None, config, Mock())
    driver.conn = Mock()
    driver.conn.recv = Mock(return_value=bytearray())
    driver.connected = True

    return driver


def test_simple(config, driver):
    driver.send_command_raw('command1', config['commands']['command1'])
    driver.conn.send.assert_called_with('VL\r\n'.encode())


def test_send_with_args(config, driver):
    driver.send_command_raw('command1', config['commands']['command1'], '12')
    driver.conn.send.assert_called_with('VL12\r\n'.encode())


def test_send_float_even(config, driver):
    driver.send_command_raw('command3', config['commands']['command3'], '12')
    driver.conn.send.assert_called_with('MV12\r\n'.encode())


def test_send_float_fract(config, driver):
    driver.send_command_raw('command3', config['commands']['command3'], '12.0')
    driver.conn.send.assert_called_with('MV12\r\n'.encode())


def test_send_with_args_decimal(config, driver):
    driver.send_command_raw('command1', config['commands']['command1'], '12.5')
    driver.conn.send.assert_called_with('VL125\r\n'.encode())


def test_output_simple(config, driver):
    result = {'output': ['VL12']}
    driver.process_result('command1', config['commands']['command1'], result)
    assert result['result'] == '12'


def test_output_multiline(config, driver):
    result = {'output': ['VL13', 'VL14', 'VL12']}
    driver.process_result('command1', config['commands']['command1'], result)
    assert result['result'] == '12'


def test_output_with_translate(config, driver):
    result = {'output': ['MPWRUP']}
    driver.process_result('command2', config['commands']['command2'], result)
    assert result['result'] == 'up'


def test_output_multiple_matches_translate(config, driver):
    result = {'output': ['MPWR12', 'MPWRON', 'MPWRUP']}
    driver.process_result('command2', config['commands']['command2'], result)
    assert result['result'] == 'up'


def test_output_multiple_matches_numeric(config, driver):
    result = {'output': ['MPWRUP', 'MPWRON', 'MPWR12']}
    driver.process_result('command4', config['commands']['command4'], result)
    assert result['result'] == '12'


def test_output_volume_whole(config, driver):
    result = {'output': ['MV12']}
    driver.process_result('current_volume', config['commands']['current_volume'], result)
    assert result['result'] == 12


def test_output_volume_half(config, driver):
    result = {'output': ['MV125']}
    driver.process_result('current_volume', config['commands']['current_volume'], result)
    assert result['result'] == 12.5


def test_output_volume_multi_line(config, driver):
    result = {'output': ['MV15', 'MVMAX80', 'MV12', 'MVMAX80']}
    driver.process_result('current_volume', config['commands']['current_volume'], result)
    assert result['result'] == 12
