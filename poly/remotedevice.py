from dataclasses import dataclass
import time
from udi_interface import LOGGER
from udi_interface.node import Node


class RemoteDevice(Node):

    @dataclass
    class Driver:
        command_name: str
        can_send: bool
        last_value: float

    def __init__(self, polyglot, primary_device, primary, address, driver_name, device_name, config, device_driver):
        super(RemoteDevice, self).__init__(polyglot, primary, address, device_name)

        self.id = driver_name

        self.driver_setters = {}
        self.command_setters = {}
        self.suffix = config.get('suffix', '')
        self.prefix = config.get('prefix', '')
        self.command_list = []
        self.commands['execute'] = RemoteDevice.execute_command_by_index

        for command_name, command_data in config.get('commands', {}).items():
            self.commands[command_name] = RemoteDevice.execute_command

            poly_data = config['poly'].get('commands', {}).get(command_name)
            if poly_data and 'driver' in poly_data:
                full_command_name = self.prefix + command_name + self.suffix
                command = device_driver.get_command(full_command_name)
                driver_name = poly_data['driver']['name']
                self.drivers.append({
                    'driver': driver_name,
                    'value': 0,
                    'uom': poly_data.get('param', {}).get('uom', 25)
                })
                if command is not None and command.get('readOnly', False):
                    self.driver_setters[driver_name] = RemoteDevice.Driver(full_command_name,
                                                                           poly_data['driver'].get('sends',
                                                                                                   False), None)
                elif 'input' in poly_data['driver'] and device_driver.hasCommand(self.prefix +
                                                                                 poly_data['driver']['input'] +
                                                                                 self.suffix):
                    self.driver_setters[driver_name] = RemoteDevice.Driver(
                        self.prefix + poly_data['driver']['input'] + self.suffix,
                        poly_data['driver'].get('sends', False), None)

            if (not command_data.get('result') and not command_data.get('acceptsNumber')
                    and not command_data.get('acceptsHex') and not command_data.get('acceptsPct')
                    and not command_data.get('acceptsFloat') and 'value_set' not in command_data):
                self.command_list.append(command_name)

        hint = config['poly'].get('hint')
        if hint:
            self.hint = hint

        self.primary_device = primary_device
        self.device_driver = device_driver

    def start(self):
        self.refresh_state()

    def stop(self):
        pass

    def execute_command_by_index(self, command):
        self.execute_command({'cmd': self.command_list[int(command['value'])]})

    def execute_command(self, command):
        try:
            LOGGER.debug('Device %s executing command %s', self.name, command['cmd'])
            self.device_driver.execute_command(self.prefix + command['cmd'] + self.suffix, command.get('value'))
            time.sleep(1)
            self.refresh_state()
        except:
            LOGGER.exception('Error sending command to ' + self.name)

    def refresh_state(self):
        if self.primary_device.connected:
            LOGGER.debug(f'Refreshing state for {self.name}')
            try:
                for driver_name, driver_data in self.driver_setters.items():
                    LOGGER.debug(f'Refreshing driver {driver_name} command {driver_data.command_name}')
                    output = self.device_driver.get_data(driver_data.command_name)
                    result = output.get('result')
                    if result is not None:
                        self.setDriver(driver_name, float(result))
                        if driver_data.can_send and driver_data.last_value != result:
                            driver_data.last_value = result
                            self.reportCmd(f'{driver_name}')
            except:
                LOGGER.exception('Error refreshing %s device state', self.name)
