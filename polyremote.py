#!/usr/bin/env python3
from poly.remotecontroller import RemoteController
import udi_interface


def PolyRemote():
    polyglot = udi_interface.Interface([])
    with open('version.txt', 'r') as version:
        polyglot.start(version.read().strip())
    RemoteController(polyglot, 'cfg/server_config.yaml')

    polyglot.runForever()


if __name__ == '__main__':
    PolyRemote()
