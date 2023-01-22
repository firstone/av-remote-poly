import copy
import importlib
from udi_interface import LOGGER
import udi_interface
import time
import utils

from polyprofile import ProfileFactory
from poly.primaryremotedevice import PrimaryRemoteDevice
from poly.remotedevice import RemoteDevice


class RemoteController(udi_interface.Node):

    def __init__(self, polyglot, config, has_devices=False):
        super(RemoteController,
              self).__init__(polyglot, 'controller', 'controller',
                             config['controller']['name'])
        self.config_data = config
        self.has_devices = has_devices
        self.device_drivers = {}
        self.device_driver_instances = {}

        self.custom_data = udi_interface.Custom(polyglot, "customdata")

        polyglot.subscribe(polyglot.START, self.start, 'controller')
        polyglot.subscribe(polyglot.STOP, self.stop)
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.process_typed_params)
        polyglot.subscribe(polyglot.CUSTOMDATA, self.process_custom_data)
        polyglot.subscribe(polyglot.CONFIG, self.process_config)
        polyglot.subscribe(polyglot.CONFIGDONE, self.process_config_done)
        polyglot.subscribe(polyglot.POLL, self.poll)

        self.init_typed_params()

        polyglot.ready()
        polyglot.addNode(self, conn_status="ST")

    def process_custom_data(self, data):
        self.custom_data.load(data)

    def process_config(self, config):
        self.config = config

    def process_config_done(self):
        self.remove_stale_nodes()
        self.create_devices()

    def process_typed_params(self, config):
        needChanges = False
        devicesConfig = self.config_data.get('devices', {})
        for driverName, paramList in config.items():
            if driverName in self.config_data['drivers']:
                for index, params in enumerate(paramList):
                    params['driver'] = driverName
                    devicesConfig[driverName + '_' + str(100 - index)] = params
            else:
                for deviceDriverName, driverData in self.config_data[
                        'drivers'].items():
                    if self.get_device_driver(deviceDriverName,
                                              driverData).processParams(
                                                  driverData,
                                                  {driverName: paramList}):
                        needChanges = True
                        for deviceDriver in self.device_driver_instances[
                                deviceDriverName].values():
                            deviceDriver.configure(driverData)

        if needChanges:
            LOGGER.debug('Regenerating profile')
            factory = ProfileFactory('.', self.config_data)
            factory.create()
            if factory.write():
                LOGGER.debug('Profile has changed. Updating')
                self.poly.installprofile()
            else:
                LOGGER.debug('Profile not changed. Skipping')

        self.config_data['devices'] = devicesConfig

    def remove_stale_nodes(self):
        if len(self.config['nodes']) == 0:
            return

        addressMap = copy.deepcopy(self.custom_data.get('addressMap', {}))
        discoveredDevices = copy.deepcopy(
            self.custom_data.get('discoveredDevices', {}))
        removedDevices = copy.deepcopy(
            self.custom_data.get('removedDevices', {}))

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

        if (self.custom_data.get('discoveredDevices') != discoveredDevices
                or self.custom_data.get('removedDevices') != removedDevices
                or self.custom_data.get('addressMap') != addressMap):
            self.custom_data['addressMap'] = addressMap
            self.custom_data['discoveredDevices'] = discoveredDevices
            self.custom_data['removedDevices'] = removedDevices

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
        if 'longPoll' in poll_flag:
            for node in self.nodes.values():
                node.refresh_state()

    def refresh_state(self):
        pass

    def is_device_configured(self, device):
        for param in self.config_data['drivers'][device['driver']].get(
                'parameters', []):
            if param.get('isRequired',
                         False) and (device[param['name']] == 0
                                     or device[param['name']] == '0'
                                     or device[param['name']] == ''):
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

    def discover(self, *args, **kwargs):
        LOGGER.debug('Starting device discovery')
        addressMap = self.custom_data.get('addressMap', {})
        discoveredDevices = copy.deepcopy(
            self.custom_data.get('discoveredDevices', {}))

        for driverName, driverData in self.config_data['drivers'].items():
            LOGGER.debug(f'Running discovery for {driverName}')
            devices = self.get_device_driver(
                driverName, driverData).discoverDevices(LOGGER)
            if devices is not None:
                discoveredDevices.update(devices)

        LOGGER.debug('Finished device discovery')
        self.custom_data['addressMap'] = addressMap
        self.custom_data['discoveredDevices'] = discoveredDevices
        self.custom_data['removedDevices'] = {}

    def create_devices(self):
        addressMap = copy.deepcopy(self.custom_data.get('addressMap', {}))
        discoveredDevices = self.custom_data.get('discoveredDevices', {})
        removedDevices = self.custom_data.get('removedDevices', {})

        devicesConfig = self.config_data.get('devices', {})
        if discoveredDevices is not None:
            devicesConfig.update(discoveredDevices)

        self.config_data['devices'] = devicesConfig
        for deviceName, deviceData in devicesConfig.items():
            if self.is_device_configured(deviceData) and deviceData.get(
                    'enable', True):
                driverName = deviceData['driver']
                deviceData.update(self.config_data['drivers'][driverName])
                polyData = self.config_data['poly']['drivers'].get(
                    driverName, {})
                deviceData['poly'].update(polyData)

                deviceDriver = self.device_driver_instances.get(
                    driverName, {}).get(deviceName)
                if deviceDriver is None:
                    deviceDriver = self.get_device_driver(
                        driverName,
                        deviceData)(utils.merge_commands(deviceData), LOGGER,
                                    True)
                    self.device_driver_instances[driverName][
                        deviceName] = deviceDriver

                nodeAddress = self.get_device_address(deviceName, addressMap)
                if nodeAddress not in removedDevices:
                    nodeName = deviceData.get('name',
                                              utils.name_to_desc(deviceName))
                    primaryDevice = PrimaryRemoteDevice(
                        self, nodeAddress, driverName, nodeName, deviceData,
                        deviceDriver)
                    self.addNode(primaryDevice)
                for commandGroup, commandGroupData in deviceData.get(
                        'commandGroups', {}).items():
                    commandGroupData['poly'] = polyData
                    groupConfig = self.config_data['poly'][
                        'commandGroups'].get(commandGroup)
                    if groupConfig:
                        groupDriverName = driverName + '_' + commandGroup
                        groupNodeAddress = self.get_device_address(
                            deviceName + '_' + commandGroup, addressMap)
                        if groupNodeAddress not in removedDevices:
                            self.addNode(
                                RemoteDevice(self, primaryDevice, nodeAddress,
                                             groupNodeAddress, groupDriverName,
                                             utils.name_to_desc(commandGroup),
                                             commandGroupData, deviceDriver))

        if self.custom_data.get('addressMap') != addressMap:
            self.custom_data['addressMap'] = addressMap
            self.custom_data['discoveredDevices'] = discoveredDevices
            self.custom_data['removedDevices'] = removedDevices

    def get_device_driver(self, driverName, deviceData):
        deviceDriver = self.device_drivers.get(driverName)
        if deviceDriver is None:
            driverModule = importlib.import_module('drivers.' + driverName)
            deviceDriver = getattr(
                driverModule,
                deviceData.get('moduleName', driverName.capitalize()))
            self.device_drivers[driverName] = deviceDriver
            self.device_driver_instances[driverName] = {}

        return deviceDriver

    id = 'controller'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
