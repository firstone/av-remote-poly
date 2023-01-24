import copy
import importlib
from udi_interface import LOGGER
import udi_interface
import utils
import yaml

from polyprofile import ProfileFactory
from poly.primaryremotedevice import PrimaryRemoteDevice
from poly.remotedevice import RemoteDevice


class RemoteController(udi_interface.Node):

    def __init__(self, polyglot, config_file, has_devices=False):
        self.config_file = config_file
        self.load_config()
        super(RemoteController, self).__init__(polyglot, 'controller', 'controller',
                                               self.config_data['controller']['name'])
        self.has_devices = has_devices
        self.device_drivers = {}
        self.device_driver_instances = {}
        self.nodes = {}

        self.custom_data = udi_interface.Custom(polyglot, "customdata")

        polyglot.subscribe(polyglot.START, self.start, 'controller')
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.process_typed_params)
        polyglot.subscribe(polyglot.CUSTOMDATA, self.process_custom_data)
        polyglot.subscribe(polyglot.CONFIG, self.process_config)
        polyglot.subscribe(polyglot.CONFIGDONE, self.process_config_done)
        polyglot.subscribe(polyglot.POLL, self.poll)

        self.init_typed_params()

        polyglot.ready()
        polyglot.addNode(self, conn_status="ST")

    def load_config(self):
        with open(self.config_file, 'r') as f:
            self.config_data = yaml.safe_load(f)

    def process_custom_data(self, data):
        self.custom_data.load(data)
        driver_data = self.custom_data['drivers']
        if driver_data is not None:
            self.load_config()
            utils.merge_objects(self.config_data['drivers'], driver_data)

    def process_config(self, config):
        self.config = config

    def process_config_done(self):
        needChanges = False
        devicesConfig = self.config_data.get('devices', {})
        for driverName, paramList in self.type_config.items():
            if driverName in self.config_data['drivers']:
                for index, params in enumerate(paramList):
                    params['driver'] = driverName
                    devicesConfig[driverName + '_' + str(100 - index)] = params
            else:
                for deviceDriverName, driverData in self.config_data['drivers'].items():
                    if self.get_device_driver(deviceDriverName,
                                              driverData).processParams(driverData, {driverName: paramList}):
                        needChanges = True
                        for deviceDriver in self.device_driver_instances[deviceDriverName].values():
                            deviceDriver.configure(driverData)

        if needChanges:
            self.save_profile()

        self.config_data['devices'] = devicesConfig

        self.create_devices()
        self.remove_stale_nodes()

    def process_typed_params(self, config):
        if config is None:
            return

        self.type_config = config

    def save_driver_data(self, driver_name, data):
        driver_data = self.custom_data.get('drivers')
        if driver_data is None:
            driver_data = {}
        driver_data[driver_name] = data
        self.custom_data['drivers'] = driver_data
        self.config_data['drivers'].update(driver_data)

    def save_profile(self):
        LOGGER.debug('Regenerating profile')
        factory = ProfileFactory('.', self.config_data)
        factory.create()
        if factory.write():
            LOGGER.debug('Profile has changed. Updating')
            self.poly.installprofile()
        else:
            LOGGER.debug('Profile not changed. Skipping')

    def remove_stale_nodes(self):
        if len(self.config['nodes']) == 0:
            return

        addressMap = copy.deepcopy(self.get_custom_data('addressMap', {}))
        discoveredDevices = copy.deepcopy(self.get_custom_data('discoveredDevices', {}))
        removedDevices = copy.deepcopy(self.get_custom_data('removedDevices', {}))

        # enumerate existing nodes
        existingNodes = {}
        for node in self.config['nodes']:
            existingNodes[node['address']] = 1

        # mark nodes in address map as known
        for item in addressMap.values():
            if item['address'] in existingNodes:
                item['known'] = True

        # enumerate stale / non-existing nodes
        staleNodes = {}
        for nodeAddress, node in self.nodes.items():
            if nodeAddress not in existingNodes:
                staleNodes[nodeAddress] = 1

        # remove known but stale nodes
        for deviceName, item in addressMap.items():
            if item['known'] and item['address'] in staleNodes:
                LOGGER.debug('Removing stale node ' + item['address'])
                discoveredDevices.pop(deviceName, None)
                removedDevices[item['address']] = 1
                del self.nodes[item['address']]

        if self.custom_data.get('discoveredDevices') != discoveredDevices:
            self.custom_data['discoveredDevices'] = discoveredDevices

        if self.custom_data.get('removedDevices') != removedDevices:
            self.custom_data['removedDevices'] = removedDevices

        if self.custom_data.get('addressMap') != addressMap:
            self.custom_data['addressMap'] = addressMap

    def init_typed_params(self):
        params = []
        for driverName, driverData in self.config_data['drivers'].items():
            values = driverData.get('parameters')
            if values:
                param = {
                    'name': driverName,
                    'title': driverData.get('description', ''),
                    'isList': True,
                    'params': values
                }
                params.append(param)
            params.extend(driverData.get('driverParameters', []))

        udi_interface.Custom(self.poly, "customtypedparams").load(params, True)

        self.setDriver('ST', 1)

    def start(self):
        self.setDriver('ST', 1)

    def poll(self, poll_flag):
        LOGGER.debug(f'poll event {poll_flag}')
        if 'longPoll' in poll_flag:
            for node in self.nodes.values():
                node.refresh_state()

    def refresh_state(self):
        pass

    def is_device_configured(self, device):
        for param in self.config_data['drivers'][device['driver']].get('parameters', []):
            if param.get('isRequired', False) and (device[param['name']] == 0 or device[param['name']] == '0' or
                                                   device[param['name']] == ''):
                return False
        return True

    def get_device_address(self, deviceName, addressMap):
        item = addressMap.get(deviceName)
        if not item:
            item = {'address': "d_" + str(len(addressMap)), 'known': False}
            addressMap[deviceName] = item
        elif not isinstance(item, dict):
            item = {'address': item, 'known': False}
            addressMap[deviceName] = item

        return item['address']

    def get_custom_data(self, key, default=None):
        value = self.custom_data[key]
        if value is None:
            value = default

        return value

    def discover(self, *args, **kwargs):
        LOGGER.debug('Starting device discovery')
        discoveredDevices = copy.deepcopy(self.get_custom_data('discoveredDevices', {}))

        for driverName, driverData in self.config_data['drivers'].items():
            LOGGER.debug(f'Running discovery for {driverName}')
            devices = self.get_device_driver(driverName, driverData).discoverDevices(LOGGER)
            if devices is not None:
                discoveredDevices.update(devices)

        LOGGER.debug('Finished device discovery')
        self.custom_data['discoveredDevices'] = discoveredDevices
        self.custom_data['removedDevices'] = {}

        self.create_devices()

    def create_devices(self):
        addressMap = copy.deepcopy(self.get_custom_data('addressMap', {}))
        discoveredDevices = self.get_custom_data('discoveredDevices', {})
        removedDevices = self.get_custom_data('removedDevices', {})

        devicesConfig = self.config_data.get('devices', {})
        if discoveredDevices is not None:
            devicesConfig.update(discoveredDevices)

        self.config_data['devices'] = devicesConfig
        for deviceName, deviceData in devicesConfig.items():
            LOGGER.debug(f'processing {deviceName} {deviceData}')
            if self.is_device_configured(deviceData) and deviceData.get('enable', True):
                driverName = deviceData['driver']
                deviceData.update(self.config_data['drivers'][driverName])
                polyData = self.config_data['poly']['drivers'].get(driverName, {})
                deviceData['poly'].update(polyData)

                deviceDriver = self.device_driver_instances.get(driverName, {}).get(deviceName)
                if deviceDriver is None:
                    deviceDriver = self.get_device_driver(driverName,
                                                          deviceData)(self, utils.merge_commands(deviceData), LOGGER,
                                                                      True)
                    self.device_driver_instances[driverName][deviceName] = deviceDriver

                nodeAddress = self.get_device_address(deviceName, addressMap)
                if nodeAddress not in removedDevices:
                    nodeName = deviceData.get('name', utils.name_to_desc(deviceName))
                    primaryDevice = PrimaryRemoteDevice(self.poly, nodeAddress, driverName, nodeName, deviceData,
                                                        deviceDriver)
                    self.poly.addNode(primaryDevice)
                    self.nodes[primaryDevice.address] = primaryDevice
                    for commandGroup, commandGroupData in deviceData.get('commandGroups', {}).items():
                        commandGroupData['poly'] = polyData
                        groupConfig = self.config_data['poly']['commandGroups'].get(commandGroup)
                        if groupConfig:
                            groupDriverName = driverName + '_' + commandGroup
                            groupNodeAddress = self.get_device_address(deviceName + '_' + commandGroup, addressMap)
                            if groupNodeAddress not in removedDevices:
                                device = RemoteDevice(self.poly, primaryDevice,
                                                      nodeAddress, groupNodeAddress, groupDriverName,
                                                      utils.name_to_desc(commandGroup), commandGroupData, deviceDriver)
                                self.poly.addNode(device)
                                self.nodes[device.address] = device
                    primaryDevice.start()

        if self.custom_data.get('addressMap') != addressMap:
            self.custom_data['addressMap'] = addressMap

    def get_device_driver(self, driverName, deviceData):
        deviceDriver = self.device_drivers.get(driverName)
        if deviceDriver is None:
            driverModule = importlib.import_module('drivers.' + driverName)
            deviceDriver = getattr(driverModule, deviceData.get('moduleName', driverName.capitalize()))
            self.device_drivers[driverName] = deviceDriver
            self.device_driver_instances[driverName] = {}

        return deviceDriver

    id = 'controller'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
