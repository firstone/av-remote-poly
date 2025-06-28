from drivers.onkyo_avr import OnkyoAVR


class OnkyoAVRNew(OnkyoAVR):

    def process_result(self, command_name, command, result):
        self.decode_result(command_name, command, result)

        if result['output'] is None or len(result['output']) == 0:
            return

        if command_name.startswith('current_volume'):
            result['output'] = float(result['output']) / 2

        super().process_result(command_name, command, result)
