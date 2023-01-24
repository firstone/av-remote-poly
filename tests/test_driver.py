import copy
import pytest
from unittest.mock import call, MagicMock

from drivers.base_driver import BaseDriver


@pytest.fixture
def config(config_data):
    return config_data['driver']


@pytest.fixture
def num_config(config_data):
    return config_data['numberParams']


@pytest.fixture
def driver_factory(config):

    def inner(config=config, return_value=None, use_numeric_key=False):
        driver = BaseDriver(None, config, None, use_numeric_key)
        driver.sendCommandRaw = MagicMock(return_value=return_value)

        return driver

    return inner


@pytest.fixture
def driver(config, driver_factory):
    return driver_factory(config, 'some_value')


def test_simple(driver):
    assert len(driver.getData('commands')['commands']) == 7


def test_execute_command(config, driver):
    driver.executeCommand('command1')
    driver.sendCommandRaw.assert_called_with('command1', config['commands']['command1'], None)


def test_execute_command_list(config, driver):
    driver.executeCommand('command7')
    sub_command = copy.deepcopy(config['commands']['command7']['commands'][0])
    sub_command['has_more'] = True
    driver.sendCommandRaw.assert_has_calls(
        [call('command7', sub_command, None),
         call('command7', config['commands']['command7']['commands'][1], None)])


def test_execute_command_with_arg_no_translate(config, driver):
    driver.executeCommand('command1', 'arg')
    driver.sendCommandRaw.assert_called_with('command1', config['commands']['command1'], 'arg')


def test_execute_command_with_arg_translate_failed(config, driver):
    driver.executeCommand('command2', 'arg')
    driver.sendCommandRaw.assert_called_with('command2', config['commands']['command2'], 'arg')


def test_execute_command_translate(config, driver):
    driver.executeCommand('command2', 'key1')
    driver.sendCommandRaw.assert_called_with('command2', config['commands']['command2'], 'value1')


def test_execute_command_translate_numberic(config, driver_factory):
    driver = driver_factory(config, None, True)
    driver.executeCommand('command2', '0')
    driver.sendCommandRaw.assert_called_with('command2', config['commands']['command2'], 'value1')


def test_get_data_no_translate(config, driver):
    response = driver.getData('command3')
    assert response['output'] == 'some_value'
    assert 'result' not in response
    driver.sendCommandRaw.assert_called_with('command3', config['commands']['command3'])


def test_get_data_translate_failed(config, driver):
    response = driver.getData('command4')
    assert response['output'] == 'some_value'
    assert 'result' not in response
    driver.sendCommandRaw.assert_called_with('command4', config['commands']['command4'])


def test_get_data_translate_default(config, driver):
    response = driver.getData('command6')
    assert response['output'] == 'some_value'
    assert response['result'] == 'key6'
    driver.sendCommandRaw.assert_called_with('command6', config['commands']['command6'])


def test_get_data_translate(config, driver_factory):
    driver = driver_factory(config, 'value1')
    response = driver.getData('command4')
    assert response['output'] == 'value1'
    assert response['result'] == 'key1'
    driver.sendCommandRaw.assert_called_with('command4', config['commands']['command4'])


def test_get_data_translate_one_way(config, driver_factory):
    driver = driver_factory(config, 'value3')
    response = driver.getData('command5')
    assert response['output'] == 'value3'
    assert response['result'] == 'key3'
    driver.sendCommandRaw.assert_called_with('command5', config['commands']['command5'])


def test_get_data_translate_numeric(config, driver_factory):
    driver = driver_factory(config, 'value1', use_numeric_key=True)
    response = driver.getData('command4')
    assert response['output'] == 'value1'
    assert response['result'] == '0'
    driver.sendCommandRaw.assert_called_with('command4', config['commands']['command4'])


def test_execute_command_bool_param(num_config, driver_factory):
    driver = driver_factory(num_config)
    driver.executeCommand('boolCommand', 'on')
    driver.sendCommandRaw.assert_called_with('boolCommand', num_config['commands']['boolCommand'], True)


def test_execute_command_bool_param_translate(num_config, driver_factory):
    driver = driver_factory(num_config)
    driver.executeCommand('boolCommandTranslate', '1')
    driver.sendCommandRaw.assert_called_with('boolCommandTranslate', num_config['commands']['boolCommandTranslate'],
                                             True)


def test_execute_command_int_param(num_config, driver_factory):
    driver = driver_factory(num_config)

    driver.executeCommand('intCommand', '123')
    driver.sendCommandRaw.assert_called_with('intCommand', num_config['commands']['intCommand'], 123)


def test_execute_command_hex_param(num_config, driver_factory):
    driver = driver_factory(num_config, '0')

    driver.executeCommand('hexCommand', '11')
    driver.sendCommandRaw.assert_called_with('hexCommand', num_config['commands']['hexCommand'], 'B')


def test_execute_command_float_param(num_config, driver_factory):
    driver = driver_factory(num_config, '0')

    driver.executeCommand('floatCommand', '1.1')
    driver.sendCommandRaw.assert_called_with('floatCommand', num_config['commands']['floatCommand'], '1.1')


def test_execute_command_float_param_no_fract(num_config, driver_factory):
    driver = driver_factory(num_config, '0')

    driver.executeCommand('floatCommand', '1')
    driver.sendCommandRaw.assert_called_with('floatCommand', num_config['commands']['floatCommand'], '1')


def test_get_data_int_param(num_config, driver_factory):
    driver = driver_factory(num_config, '123')

    response = driver.getData('intResult')
    assert response['result'] == 123


def test_get_data_hex_param(num_config, driver_factory):
    driver = driver_factory(num_config, '12')

    response = driver.getData('hexResult')
    assert response['result'] == 18


def test_get_data_float_param(num_config, driver_factory):
    driver = driver_factory(num_config, '1.2')

    response = driver.getData('floatResult')
    assert response['result'] == 1.2
