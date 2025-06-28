import copy
from drivers.param_parser import ParamParser


class BaseDriver(object):

    def __init__(self, controller, config, logger, use_numeric_key=False):
        self.controller = controller
        self.config = config
        self.use_numeric_key = use_numeric_key
        self.connected = False
        self.logger = logger
        self.configure()

    def configure(self, data=None):
        if data is not None:
            self.config.update(data)

        self.param_parser = ParamParser(self.config, self.use_numeric_key)
        self.connection_desc = (self.config.get('hostName', '') + ':' + str(self.config.get('port', 0)))

    def start(self):
        try:
            if not self.connected:
                self.connect()
        except Exception:
            self.logger.exception('Connection to %s failed', self.connection_desc)

    def connect(self):
        pass

    def disconnect(self):
        pass

    def is_connected(self):
        try:
            if not self.connected:
                self.connect()
        except Exception:
            try:
                self.disconnect()
            except Exception:
                pass

        return self.connected

    def has_command(self, command_name):
        return command_name in self.config['commands']

    def get_command(self, command_ame):
        return self.config['commands'].get(command_ame)

    def get_data(self, command_name, args=None):
        if command_name == 'commands':
            command_list = []
            for cmd_name, command in self.config['commands'].items():
                command_list.append({'name': cmd_name, 'method': 'GET' if command.get('result', False) else 'PUT'})
            return {'driver': self.__class__.__name__, 'commands': command_list}

        command = self.config['commands'][command_name]
        if not command.get('result'):
            raise RuntimeError('Invalid command for ' + __name__ + ' and method: ' + command_name)

        result = {
            'driver': self.__class__.__name__,
            'command': command_name,
        }

        try:
            result['output'] = self.send_command_raw(command_name, command)
            self.process_result(command_name, command, result)
        except:
            self.connected = False
            raise
        return result

    def send_command_raw(self, command_name, command, args=None):
        pass

    def execute_command(self, command_name, args=None):
        command = self.config['commands'][command_name]

        if args is not None:
            args = self.param_parser.translate_param(command, str(args))

            if command.get('acceptsBool') and type(args) is not bool:
                args = args == 'true' or args == 'on'
            elif command.get('acceptsNumber'):
                args = int(args)
            elif command.get('acceptsPct'):
                args = float(args) / 100
            elif command.get('acceptsFloat'):
                args = '{0:g}'.format(float(args))
            elif command.get('acceptsHex'):
                args = hex(int(args))[2:].upper()

        result = {
            'driver': __name__,
            'command': command_name,
        }

        try:
            if 'commands' in command:
                commands = copy.deepcopy(command['commands'])

                for sub_command in commands[:-1]:
                    sub_command['has_more'] = True
                    self.send_command_raw(command_name, sub_command, args)

                result['output'] = self.send_command_raw(command_name, commands[-1], args)
            else:
                result['output'] = self.send_command_raw(command_name, command, args)
            self.process_result(command_name, command, result)
        except:
            self.connected = False
            raise

        if args is not None:
            result['args'] = args

        return result

    def process_result(self, command_name, command, result):
        output = None
        try:
            if command.get('acceptsNumber'):
                output = int(result['output'])
            elif command.get('acceptsFloat'):
                output = float(result['output'])
            elif command.get('acceptsPct'):
                output = int(float(result['output']) * 100)
            elif command.get('acceptsHex'):
                output = int(result['output'], 16)
            else:
                output = self.param_parser.translate_param(command, result['output'], None, False)
        except Exception:
            pass

        if output is not None:
            result['result'] = output

    @staticmethod
    def process_params(config, param):
        return False

    @staticmethod
    def discover_devices(logger):
        return None
