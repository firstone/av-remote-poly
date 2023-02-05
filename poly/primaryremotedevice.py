from poly.remotedevice import RemoteDevice


class PrimaryRemoteDevice(RemoteDevice):

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]

    def __init__(self, polyglot, address, driver_name, device_name, config, device_driver):
        super(PrimaryRemoteDevice, self).__init__(polyglot, self, address, address, driver_name, device_name, config,
                                                  device_driver)
        self.connected = False

    def start(self):
        self.device_driver.start()
        self.refresh_state()

    def stop(self):
        self.setDriver('ST', 0)

    def refresh_state(self):
        self.connected = self.device_driver.is_connected()
        self.setDriver('ST', 1 if self.connected else 0)
        super(PrimaryRemoteDevice, self).refresh_state()
