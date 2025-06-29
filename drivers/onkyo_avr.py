import socket
import struct

from drivers.base_driver import BaseDriver
import utils


class OnkyoAVR(BaseDriver):

    ISCP_SIGNATURE = 'ISCP'
    ISCP_VERSION = 1
    ISCP_HEADER = struct.Struct(">4sIIB3x")
    DESTINATION_UNIT_TYPE = '!1'
    CMD_LEN = 3
    RESPONSE_DATA_OFFSET = ISCP_HEADER.size + len(DESTINATION_UNIT_TYPE) + CMD_LEN
    RECEIVE_BUFFER_SIZE = 1024
    SEARCH_SUFFIX = 'QSTN'

    def __init__(self, controller, config, logger, use_numeric_key=False):
        super().__init__(controller, config, logger, use_numeric_key)

        self.conn = None
        logger.info('Loaded %s driver', self.__class__.__name__)

    def connect(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.config['hostName'], self.config['port']))
        self.conn.settimeout(self.config['timeout'])
        self.connected = True

    def send_command_raw(self, command_name, command, args=None):
        if not self.connected:
            self.connect()

        result = ''
        try:
            self.logger.debug("%s executing command %s (%s, %s)", self.__class__.__name__, command_name,
                              command['code'], args)
            command_str = command['code']
            if args:
                command_str += args
            request = self.convert_to_iscp(command_str)
            self.logger.debug("%s sending %s", self.__class__.__name__, request)
            self.conn.send(self.convert_to_iscp(command_str))
            result_buf = self.conn.recv(OnkyoAVR.RECEIVE_BUFFER_SIZE)
            self.logger.debug("%s received %s", self.__class__.__name__, result_buf)
            result = result_buf.decode()
        except socket.timeout:
            pass

        return result

    def convert_to_iscp(self, str_data):
        str_data = OnkyoAVR.DESTINATION_UNIT_TYPE + str_data + '\r'
        data = OnkyoAVR.ISCP_HEADER.pack(OnkyoAVR.ISCP_SIGNATURE.encode(), OnkyoAVR.ISCP_HEADER.size, len(str_data),
                                         OnkyoAVR.ISCP_VERSION)
        return data + str_data.encode()

    def decode_result(self, command_name, command, result):
        if len(result['output']) == 0:
            return

        result_buf = result['output'].encode()
        results = []
        while len(result_buf) > 0:
            try:
                (_, _, response_len, _) = OnkyoAVR.ISCP_HEADER.unpack(result_buf[:OnkyoAVR.ISCP_HEADER.size])
                # strip first 2 chars last 3 chars for \x1a\r\n
                results.append(result_buf[OnkyoAVR.ISCP_HEADER.size +
                                          len(OnkyoAVR.DESTINATION_UNIT_TYPE):OnkyoAVR.ISCP_HEADER.size + response_len -
                                          3].decode())
                result_buf = result_buf[OnkyoAVR.ISCP_HEADER.size + response_len:]
            except Exception:
                self.logger.error("Error processing buffer. "
                                  "Possibly incomplete buffer. Increase receive buffer size")
                break

        result['output'] = utils.get_last_output(command, results, self.param_parser.value_sets, OnkyoAVR.SEARCH_SUFFIX)

    def process_result(self, command_name, command, result):
        self.decode_result(command_name, command, result)

        if result['output'] is not None and len(result['output']) > 0:
            super().process_result(command_name, command, result)
