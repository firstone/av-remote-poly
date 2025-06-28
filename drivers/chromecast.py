import pychromecast
from pychromecast.discovery import stop_discovery

from drivers.base_driver import BaseDriver
import utils


class Chromecast(BaseDriver):

    APPS_KEY_NAME = 'chromecastApps'
    PLAYLISTS_KEY_NAME = 'chromecastPlaylists'
    ENABLED_KEY_NAME = 'enableChromecastSupport'
    CAST_CONNECT_TRIES = 1
    CAST_CONNECT_TIMEOUT = 5

    enabled = False

    def __init__(self, controller, config, logger, use_numeric_key=False):
        super(Chromecast, self).__init__(controller, config, logger, use_numeric_key)

        self.cast = None

        logger.info('Loaded %s driver', self.__class__.__name__)

    def send_command_raw(self, command_name, command, args=None):
        if command_name == 'start_app':
            if args == '':
                return ''

            if not args:
                return self.send_command_raw('quit_app', self.config['commands']['quit_app'])

        elif command_name == 'toggle_mute':
            current_mute = self.send_command_raw('current_mute', self.config['commands']['current_mute'])
            return self.send_command_raw('set_mute', self.config['commands']['set_mute'], not current_mute)

        controller_name = command.get('controller')
        controller = getattr(self.cast, controller_name) if controller_name else self.cast
        attr = getattr(controller, command['code'])

        try:
            if command.get('result', False):
                result = getattr(attr, command['argKey'], '')
                return result
            elif args is not None:
                if isinstance(args, list):
                    attr(*args)
                else:
                    attr(args)
            else:
                attr()
        except Exception:
            self.disconnect()

        return ''

    def is_connected(self):
        self.connected = False if self.cast is None else self.cast.socket_client.is_connected

        return super(Chromecast, self).is_connected()

    def connect(self):
        self.connected = False

        if self.cast is None:
            device_name = self.config['name']
            casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[device_name],
                                                                 tries=Chromecast.CAST_CONNECT_TRIES)
            stop_discovery(browser)
            if not casts:
                self.logger.debug(f'Device not found: {device_name}')
                return

            self.cast = casts[0]

        self.cast.wait(Chromecast.CAST_CONNECT_TIMEOUT)
        self.connected = self.cast.socket_client.is_connected
        if not self.connected:
            self.disconnect()

    def disconnect(self):
        try:
            self.cast.disconnect()
        except Exception:
            pass
        self.cast = None

    @staticmethod
    def process_params(config, param):
        config_changed = False
        config.setdefault('values', {})

        playlists = param.get(Chromecast.PLAYLISTS_KEY_NAME)
        if playlists is not None:
            values = []
            for playlist in playlists:
                values.append({'value': playlist['name'], 'param': [playlist['url'], playlist['type']]})
            if config['values'].get(Chromecast.PLAYLISTS_KEY_NAME) != values:
                config['values'][Chromecast.PLAYLISTS_KEY_NAME] = values
                config_changed = True

        apps = param.get(Chromecast.APPS_KEY_NAME)
        if apps is not None:
            values = list(config.get('coreApps', []))

            for app in apps:
                values.append({'value': app['name'], 'param': app['app_id']})

            default_app = config.get('defaultApp')
            if default_app:
                values.append(default_app)

            if config['values'].get(Chromecast.APPS_KEY_NAME) != values:
                config['values'][Chromecast.APPS_KEY_NAME] = values
                config_changed = True

        enabled = param.get(Chromecast.ENABLED_KEY_NAME)
        if enabled is not None:
            Chromecast.enabled = enabled

        return config_changed

    @staticmethod
    def discover_devices(logger):
        if not Chromecast.enabled:
            logger.debug('Chromecast disabled')
            return None

        casts, browser = pychromecast.get_chromecasts(Chromecast.CAST_CONNECT_TRIES)
        stop_discovery(browser)

        result = {}
        for cast in casts:
            friendly_name = cast.cast_info.friendly_name
            logger.debug(f'Found Chromecast device {friendly_name}')
            result[utils.desc_to_name(friendly_name)] = {'name': friendly_name, 'driver': 'chromecast'}

        return result
