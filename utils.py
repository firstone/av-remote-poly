import copy
import errno
import os


def flatten_commands(config):
    config.setdefault('commands', {})
    commands = config['commands']
    for commandGroup in config.get('commandGroups', {}).values():
        prefix = commandGroup.get('prefix', '')
        suffix = commandGroup.get('suffix', '')
        for key, value in commandGroup['commands'].items():
            commands[prefix + key + suffix] = value


def merge_commands(config):
    result = copy.deepcopy(config)
    flatten_commands(result)

    return result


def name_to_desc(name):
    labels = name.split('_')
    return ' '.join([label.capitalize() for label in labels])


def name_to_nls(name):
    nls = ''.join(name.split('_')).upper()

    return nls


def desc_to_name(desc):
    name = '_'.join(desc.split(' ')).lower()

    return name


def create_dir(fileName):
    if not os.path.exists(os.path.dirname(fileName)):
        try:
            os.makedirs(os.path.dirname(fileName))
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


def get_last_output(command, output, value_sets, searchSuffix):
    prefix = command['code'].replace(searchSuffix, '')
    keys = value_sets.get(command.get('value_set', ''), {})
    output.reverse()

    for line in output:
        if line.startswith(prefix):
            value = line[len(prefix):]
            if (command.get('acceptsNumber', False) or command.get('acceptsFloat', False)):
                try:
                    float(value)
                    return value
                except:
                    pass
            if command.get('acceptsHex', False):
                try:
                    int(value, 16)
                    return value
                except:
                    pass
            elif keys.get(value) is not None:
                return value

    return None


def merge_objects(obj_to, obj_from):
    for key, val in obj_from.items():
        if key in obj_to:
            if isinstance(val, list):
                obj_to[key].extend(val)
            else:
                merge_objects(obj_to[key], val)
        else:
            obj_to[key] = val
