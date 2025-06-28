import socket
import time

from drivers.base_driver import BaseDriver
import utils


class DenonAVR(BaseDriver):

    BUF_SIZE = 4096
    RESPONSE_DELAY = .15
    CLOSE_DELAY = .15
    SEARCH_SUFFIX = '?'

    def __init__(self, controller, config, logger, use_numeric_key=False):
        super().__init__(controller, config, logger, use_numeric_key)

        self.conn = None
        logger.info('Loaded %s driver', self.__class__.__name__)

    def is_connected(self):
        result = super(DenonAVR, self).is_connected()
        self.auto_close()

        return result

    def connect(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.logger.debug("Connecting to %s:%s", self.config['hostName'], self.config['port'])
        self.conn.connect((self.config['hostName'], self.config['port']))
        self.conn.settimeout(self.config['timeout'])
        self.connected = True

    def auto_close(self):
        if self.config.get('connectOnDemand', False):
            self.conn.close()
            self.connected = False
            time.sleep(self.CLOSE_DELAY)

    def send_command_raw(self, command_name, command, args=None):
        if not self.connected:
            self.connect()

        result = ''
        try:
            command_str = command['code']
            if args:
                if command.get('acceptsFloat', False):
                    command_str += '{0:g}'.format(float(args)).replace('.', '')
                else:
                    command_str += args
            self.logger.debug("%s sending %s", self.__class__.__name__, command_str)
            command_str += '\r\n'
            self.conn.send(command_str.encode())
            time.sleep(self.RESPONSE_DELAY)
            result = self.conn.recv(self.BUF_SIZE).decode()
            self.auto_close()
            self.logger.debug("%s received %s", self.__class__.__name__, result.replace('\r', '\\r'))
        except socket.timeout:
            pass
        return result[:-1].split('\r') if result else [result]

    def process_result(self, command_name, command, result):
        if len(result) == 0:
            return

        if command_name.startswith('current_volume'):
            output = utils.get_last_output(command, result['output'], self.param_parser.value_sets,
                                           DenonAVR.SEARCH_SUFFIX)

            if output is None:
                return

            if len(output) > 2:
                output = output[:2] + '.5'
            else:
                output = output + '.0'
            output = float(output)
        else:
            output = self.param_parser.translate_param(
                command,
                utils.get_last_output(command, result['output'], self.param_parser.value_sets, DenonAVR.SEARCH_SUFFIX))

        if output:
            result['result'] = output
