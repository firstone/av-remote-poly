import pytest
import sys
from unittest.mock import Mock, MagicMock

import udi_interface

from poly.remotedevice import RemoteDevice

sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
udi_interface.LOGGER.handlers = []


@pytest.fixture
def device_factory(config_data):

    def inner(key, cmd_key, suffix_key=None, return_value={}, has_command=True):
        data = config_data[key]
        if suffix_key is not None:
            data = data['commandGroups'][suffix_key]

        driver = Mock()
        primaryDevice = Mock()
        poly = MagicMock()
        driver.get_command = MagicMock(return_value=data['commands'][cmd_key])
        if not has_command:
            driver.has_command = Mock(return_value=False)
        driver.get_data = MagicMock(return_value=return_value)
        device = RemoteDevice(poly, primaryDevice, None, None, None, "test device", data, driver)

        return device, driver

    return inner


def test_simple(device_factory):
    device, driver = device_factory('simple', 'command1')

    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('command1', None)


def test_read_only(device_factory):
    device, driver = device_factory('read_only', 'command3')

    device.runCmd({'cmd': 'command3'})
    driver.execute_command.assert_called_with('command3', None)
    assert device.driver_setters['GV0'].command_name == 'command3'


def test_state(device_factory):
    device, driver = device_factory('state', 'command1', return_value={'result': 1})
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('command1', None)
    driver.get_data.assert_called_with('command2')


def test_suffix(device_factory):
    device, driver = device_factory('suffix', 'command1', 'group1', {'result': 1})
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('command1_g1', None)
    driver.get_data.assert_called_with('command2_g1')


def test_read_only_suffix(device_factory):
    device, driver = device_factory('read_only_suffix', 'command1', 'group1')
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('command1_r1', None)
    assert device.driver_setters['GV0'].command_name == 'command1_r1'


def test_prefix(device_factory):
    device, driver = device_factory('prefix', 'command1', 'group1', {'result': 1})
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('g1_command1', None)
    driver.get_data.assert_called_with('g1_command2')


def test_read_only_prefix(device_factory):
    device, driver = device_factory('read_only_prefix', 'command1', 'group1')
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('r1_command1', None)
    assert device.driver_setters['GV0'].command_name == 'r1_command1'


def test_skips_bad_input_command(device_factory):
    device, driver = device_factory('state', 'command1', return_value={'result': 1}, has_command=False)
    device.runCmd({'cmd': 'command1'})
    driver.execute_command.assert_called_with('command1', None)
    driver.get_data.assert_not_called()
