from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen
import asyncio
import os

from drivers.base_driver import BaseDriver


class Android(BaseDriver):

    WINDOW_RECORD = 'Window '
    ON_SCREEN_RECORD = 'isOnScreen=true'
    MEDIA_STATE_RECORD = 'state=PlaybackState'
    KEY_FILE_NAME = '.androidKey'
    TRANSPORT_TIMEOUT = 30
    AUTH_TIMEOUT = 60
    AAPT_FILE_NAME = 'aapt-arm-pie'
    AAPT_FULL_NAME = '/data/local/tmp/' + AAPT_FILE_NAME

    def __init__(self, controller, config, logger, use_numeric_key=False):
        super(Android, self).__init__(controller, config, logger, use_numeric_key)

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        logger.info('Loaded %s driver', __name__)

    def init_signer(self):
        if not os.path.isfile(Android.KEY_FILE_NAME):
            keygen(Android.KEY_FILE_NAME)

        with open(Android.KEY_FILE_NAME, 'r') as f:
            priv = f.read()

        with open(Android.KEY_FILE_NAME + '.pub', 'r') as f:
            pub = f.read()

        self.signer = PythonRSASigner(pub, priv)

        # Connect

    def connect(self):
        self.init_signer()

        async def do_connect():
            self.device = AdbDeviceTcpAsync(self.config['hostName'],
                                            self.config['port'],
                                            default_transport_timeout_s=Android.TRANSPORT_TIMEOUT)
            await self.device.connect(rsa_keys=[self.signer], auth_timeout_s=Android.AUTH_TIMEOUT)
            if self.device.available:
                self.connected = True

        if self.loop.is_running():
            self.loop.stop()

        self.loop.run_until_complete(do_connect())

    async def send_key(self, commandName, args):
        code = args if args else self.config['commands'][commandName]['code']
        result = await self.device.shell(f'input keyevent {code}')

        return result

    def send_command_raw(self, commandName, command, args=None):
        if not self.connected:
            self.connect()

        if self.loop.is_running():
            self.loop.stop()
        f = getattr(self, commandName, None)
        if f is not None:
            result = self.loop.run_until_complete(f(args))
        else:
            result = self.loop.run_until_complete(self.send_key(commandName, args))

        return result

    async def start_app(self, args):
        # self.logger.debug(f'Starting app {args}')
        result = await self.device.shell(f'am start -n {args}')
        # self.logger.debug(result)

        return result

    async def check_file(self, file_name):
        output = await self.device.shell(f'ls -la {file_name}')
        return output.split('\n')[0].find('No such file or directory') < 0

    async def upload_file(self, file_name, remote_file):
        await self.device.push(file_name, remote_file)
        await self.device.shell(f'chmod 0755 {remote_file}')

    async def get_media_state(self, _):
        output = await self.device.shell(f'dumpsys media_session')
        for line in output.split('\n'):
            pos = line.find(Android.MEDIA_STATE_RECORD)
            if pos > 0:
                state = line[len(Android.MEDIA_STATE_RECORD):].split(',')[0]
                return int(state.split('=')[1])

        return 0

    async def get_current_activity(self, _):
        output = await self.device.shell(f'dumpsys window windows')
        # self.logger.debug(output)
        for line in output.split('\n'):
            pos = line.find(Android.WINDOW_RECORD)
            if pos > 0:
                window_record = line.strip()

            pos = line.find(Android.ON_SCREEN_RECORD)
            if pos > 0:
                values = window_record.split(' ')
                activity = values[4][:-2].split('/')[0]
                self.logger.debug(f'current activtty {activity}')
                return activity

        return ''

    async def get_app_list(self, _):
        if not self.connected:
            self.connect()

        if await self.check_file(Android.AAPT_FULL_NAME):
            self.logger.debug('aapt file presend')
        else:
            self.logger.debug('Uploading aapt file')
            await self.upload_file(Android.AAPT_FILE_NAME, Android.AAPT_FULL_NAME)

        output = await self.device.shell('pm list packages -3')
        app_list = []
        for line in output.split('\n'):
            vals = line.split(':')
            if len(vals) > 1:
                app_list.append({'appName': vals[1], 'activity': []})

        for app_info in app_list:
            self.logger.debug("Processing %s app", app_info['appName'])
            output = await self.device.shell(f'pm dump {app_info["appName"]}')
            lines = output.split('\n')
            for index, line in enumerate(lines):
                pos = line.find('codePath')
                if pos > 0:
                    app_info['codePath'] = line[pos + 9:] + '/base.apk'
                elif line.find('MAIN:') > 0:
                    activity_line = lines[index + 1]
                    pos = activity_line.find(app_info['appName'] + '/')
                    if pos > 0:
                        app_info['activity'].append(activity_line[activity_line.find('/', pos) +
                                                                  1:activity_line.find(' ', pos)])
            output = await self.device.shell(f'{Android.AAPT_FULL_NAME} d badging {app_info["codePath"]}')
            for line in output.split('\n'):
                if line.strip().find('application-label:') >= 0:
                    app_info['label'] = line.split(':')[1][1:-1]

        activities = []
        inputs = []
        for app_info in app_list:
            label = app_info.get('label')
            activity = app_info.get('activity')
            if label is not None and len(activity) > 0:
                activities.append({'value': label, 'param': app_info['appName']})
                inputs.append({'value': label, 'param': app_info['appName'] + '/' + activity[0]})

        driver_config = {
            'values': {
                'activities': activities
            },
            'commandGroups': {
                'inputs': {
                    'commands': {
                        'start_app': {
                            'values': inputs
                        }
                    }
                }
            }
        }

        self.controller.save_driver_data('android', driver_config)
        self.controller.save_profile()
