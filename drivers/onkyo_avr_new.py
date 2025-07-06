from drivers.onkyo_avr import OnkyoAVR
from drivers.base_driver import BaseDriver


class OnkyoAVRNew(OnkyoAVR):

    def process_result(self, command_name, command, result):
        self.decode_result(command_name, command, result)

        if result['output'] is None or len(result['output']) == 0:
            return

        BaseDriver.process_result(self, command_name, command, result)

        if command_name.startswith('current_volume'):
            result['result'] = float(result['result']) / 2
