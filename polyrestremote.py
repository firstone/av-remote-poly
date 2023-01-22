#!/usr/bin/env python3
from poly.remotecontroller import RemoteController
import udi_interface
import yaml


def PolyRemote():
    config_data = yaml.safe_load('cfg/server_config.yaml')

    polyglot = udi_interface.Interface([])
    with open('version.txt', 'r') as version:
        polyglot.start(version.read().strip())
    RemoteController(polyglot, config_data)
    polyglot.runForever()


if __name__ == '__main__':
    PolyRemote()
