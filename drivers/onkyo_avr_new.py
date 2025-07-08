from drivers.onkyo_avr import OnkyoAVR
from drivers.base_driver import BaseDriver


class OnkyoAVRNew(OnkyoAVR):

    def send_command_raw(self, command_name, command, args=None):
        if command_name.startswith('set_volume') and args is not None:
            args = hex(int(float(args) * 2))[2:].upper()

        super().send_command_raw(command_name, command, args)

    def process_result(self, command_name, command, result):
        self.decode_result(command_name, command, result)

        if result['output'] is None or len(result['output']) == 0:
            return

        if command_name.startswith('current_volume'):
            result['result'] = float(int(result['output'], 16)) / 2
            return

        BaseDriver.process_result(self, command_name, command, result)
