#!/usr/bin/env python3
import argparse
import hashlib
import os
import pathlib
import utils
import xml.etree.ElementTree as ET
import yaml

from drivers.param_parser import ParamParser


def PolyRemote():
    parser = argparse.ArgumentParser(prog='PolyRemote',
                                     description='Polyglot profile generator for AVRemote node server')
    parser.add_argument(
        '-c',
        '--config',
        type=argparse.FileType('r'),
        help='Config file',
        required=True,
    )

    parser.add_argument(
        '-d',
        '--destination',
        help='Polyglot profile destination directory',
        type=pathlib.Path,
        required=True,
    )

    args = parser.parse_args()
    print("Generating Polyglot profile")

    factory = ProfileFactory(args.destination, yaml.safe_load(args.config))
    factory.create()
    factory.write()


class ProfileFactory(object):

    NODE_NAME = 'ND-{}-NAME = {}'
    NODE_ICON = 'ND-{}-ICON = {}'
    COMMAND_NAME = 'CMD-{}-{}-NAME = {}'
    STATUS_NAME = 'ST-{}-{}-NAME = {}'
    PROFILE_DIR = 'profile'
    EDITOR_FILE = ['editor', 'editors.xml']
    NLS_FILE = ['nls', 'en_us.txt']
    NODES_FILE = ['nodedef', 'nodedefs.xml']
    COMMAND_LIST_THRESHOLD = 5

    def __init__(self, destination, config):
        self.destination = destination
        self.config = config

        self.nodeTree = ET.Element('nodeDefs')
        self.editorTree = ET.Element('editors')

        self.nlsData = []

    def create(self):
        # Write controller labels
        self.nlsData.append('# controller labels')
        self.nlsData.append('')
        self.nlsData.append(self.NODE_NAME.format('controller', self.config['controller']['name'] + ' Controller'))
        self.nlsData.append(self.NODE_ICON.format('controller', self.config['controller'].get('icon', 'GenericCtl')))
        self.nlsData.append('')
        self.nlsData.append(self.COMMAND_NAME.format('ctl', 'DISCOVER', 'Re-Discover'))
        self.nlsData.append(self.STATUS_NAME.format('ctl', 'ST', self.config['controller']['name'] + ' Status'))
        self.nlsData.append('')
        self.nlsData.append('CTRLSTATUS-0 = Offline')
        self.nlsData.append('CTRLSTATUS-1 = Online')
        self.nlsData.append('CTRLSTATUS-2 = Failed')

        # Write controller node
        nodeDef = ET.SubElement(self.nodeTree, 'nodeDef', id='controller', nls='ctl')
        sts = ET.SubElement(nodeDef, 'sts')
        ET.SubElement(sts, 'st', id='ST', editor='CTRLSTATUS')
        cmds = ET.SubElement(nodeDef, 'cmds')
        ET.SubElement(cmds, 'sends')
        accepts = ET.SubElement(cmds, 'accepts')
        ET.SubElement(accepts, 'cmd', id='DISCOVER')

        editor = ET.SubElement(self.editorTree, 'editor', id='bool')
        ET.SubElement(editor, 'range', uom='2', subset='0,1')

        editor = ET.SubElement(self.editorTree, 'editor', id='CTRLSTATUS')
        ET.SubElement(editor, 'range', uom='25', subset='0,1,2', nls='CTRLSTATUS')

        # Write primary devices
        for driverName, driverData in self.config['drivers'].items():
            polyCommandsData = self.config['poly']['drivers'].get(driverName, {}).get('commands', {})
            paramParser = ParamParser(driverData, True)
            nodeDesc = driverData.get('description', utils.name_to_desc(driverName))
            nlsName = utils.name_to_nls(driverName)
            nlsData = [self.STATUS_NAME.format(nlsName, 'ST', nodeDesc + ' Online')]
            states = self.write_node_info(polyCommandsData, paramParser, driverName, nodeDesc, nlsName, driverData,
                                          nlsData)
            ET.SubElement(states, 'st', id='ST', editor='bool')
            # Write sub devices
            for groupName, groupData in driverData.get('commandGroups', {}).items():
                polyGroupData = self.config['poly']['commandGroups'].get(groupName)
                if polyGroupData:
                    self.write_node_info(polyCommandsData, paramParser, driverName + '_' + groupName,
                                         nodeDesc + ' ' + utils.name_to_desc(groupName),
                                         utils.name_to_nls(driverName + polyGroupData.get('nls', groupName)), groupData)

    def write(self):
        has_changed = False

        nlsFile = os.path.join(self.destination, self.PROFILE_DIR, *self.NLS_FILE)
        utils.create_dir(nlsFile)

        hash = self.get_hash(nlsFile)

        with open(nlsFile, 'w') as output:
            for line in self.nlsData:
                output.write(line)
                output.write('\n')

        if hash != self.get_hash(nlsFile):
            has_changed = True

        nodesFile = os.path.join(self.destination, self.PROFILE_DIR, *self.NODES_FILE)
        utils.create_dir(nodesFile)

        hash = self.get_hash(nodesFile)

        with open(nodesFile, 'w') as output:
            output.write(ET.tostring(self.nodeTree).decode())

        if hash != self.get_hash(nodesFile):
            has_changed = True

        editorFile = os.path.join(self.destination, self.PROFILE_DIR, *self.EDITOR_FILE)
        utils.create_dir(editorFile)

        hash = self.get_hash(editorFile)

        with open(editorFile, 'w') as output:
            output.write(ET.tostring(self.editorTree).decode())

        if hash != self.get_hash(editorFile):
            has_changed = True

        return has_changed

    def write_node_info(self, polyCommandsData, paramParser, nodeName, nodeDesc, nlsName, nodeData, nlsData=[]):
        assert len(nlsName) <= 16, 'Node NLS name is too long: {}'.format(nlsName)

        self.nlsData.append('# ' + nodeName + ' labels\n')
        self.nlsData.append(self.NODE_NAME.format(nodeName, nodeDesc))
        self.nlsData.append(self.NODE_ICON.format(nodeName, nodeData.get('icon', 'GenericCtl')))
        self.nlsData.extend(nlsData)
        nodeDef = ET.SubElement(self.nodeTree, 'nodeDef', id=nodeName, nls=nlsName)
        states = ET.SubElement(nodeDef, 'sts')
        cmds = ET.SubElement(nodeDef, 'cmds')
        sends = ET.SubElement(cmds, 'sends')
        accepts = ET.SubElement(cmds, 'accepts')
        cmd_list = []
        for commandName, commandData in nodeData['commands'].items():
            commandKey = nodeName + '_' + commandName
            nlsCommand = utils.name_to_nls(commandKey)
            polyData = polyCommandsData.get(commandName, {})
            polyDriver = polyData.get('driver', {})
            polyDriverName = polyDriver.get('name')
            if not commandData.get('result'):
                self.nlsData.append(
                    self.COMMAND_NAME.format(nlsName, commandName,
                                             commandData.get('description', utils.name_to_desc(commandName))))
                cmd = ET.SubElement(accepts, 'cmd', id=commandName)
                param = None
                if (commandData.get('acceptsNumber') or commandData.get('acceptsHex') or
                        commandData.get('acceptsPct') or commandData.get('acceptsFloat')):
                    param = ET.SubElement(cmd, 'p', id='', editor=nlsCommand)
                    editor = ET.SubElement(self.editorTree, 'editor', id=nlsCommand)
                    range = ET.SubElement(editor, 'range')
                    for rangeKey, rangeValue in polyData['param'].items():
                        range.set(rangeKey, str(rangeValue))
                elif 'value_set' in commandData:
                    param = ET.SubElement(cmd, 'p', id='', editor=nlsCommand)
                    self.add_driver_desc(nlsCommand, paramParser.value_sets[commandData['value_set'] + '_names'])
                else:
                    cmd_list.append(commandName)

                if polyDriverName:
                    if param is None:
                        raise RuntimeError('Driver configured but command is not configured for parameters: ' +
                                           commandName)
                    param.set('init', polyDriverName)

            elif commandData.get('readOnly', False) and 'value_set' in commandData:
                self.add_driver_desc(
                    nlsCommand, paramParser.value_sets[commandData['value_set'].replace('_reverse', '') + '_names'])

            if polyDriverName:

                def add_element(parent, elem_name, fmt_string, set_editor=True):
                    attr = {'id': polyDriverName}
                    if set_editor:
                        attr['editor'] = nlsCommand
                    ET.SubElement(parent, elem_name, attr)
                    self.nlsData.append(
                        fmt_string.format(nlsName, polyDriverName,
                                          polyData['driver'].get('description', utils.name_to_desc(commandName))))

                add_element(states, 'st', self.STATUS_NAME)
                if polyDriver.get('sends'):
                    add_element(sends, 'cmd', self.COMMAND_NAME, False)

        if len(cmd_list) > self.COMMAND_LIST_THRESHOLD:
            nlsCommand = nlsName + '_C'
            for cmd_index, commandName in enumerate(cmd_list):
                self.nlsData.append(nlsCommand + '-' + str(cmd_index) + ' = ' +
                                    commandData.get('description', utils.name_to_desc(commandName)))
            self.nlsData.append(self.COMMAND_NAME.format(nlsName, 'execute', 'Send Command'))
            cmd = ET.SubElement(accepts, 'cmd', id='execute')
            param = ET.SubElement(cmd, 'p', id='', editor=nlsCommand)
            editor = ET.SubElement(self.editorTree, 'editor', id=nlsCommand)
            range = ET.SubElement(editor, 'range')
            range.set('nls', nlsCommand)
            range.set('uom', '25')
            range.set('subset', '0-' + str(len(cmd_list) - 1))

        self.nlsData.append('')
        return states

    def add_driver_desc(self, nlsCommand, names):
        editor = ET.SubElement(self.editorTree, 'editor', id=nlsCommand)
        maxIndex = 0
        for key, value in names.items():
            if key.isdigit():
                maxIndex += 1
                self.nlsData.append(nlsCommand + '_I-' + str(key) + ' = ' + str(value))
        maxIndex = maxIndex - 1 if maxIndex else 0
        ET.SubElement(editor, 'range', uom='25', subset='0-' + str(maxIndex), nls=nlsCommand + '_I')

    def get_hash(self, file_name):
        if not os.path.isfile(file_name):
            return ''

        hash = hashlib.sha256()
        with open(file_name, 'rb') as file:
            hash.update(file.read())

        return hash.hexdigest()


if __name__ == '__main__':
    PolyRemote()
