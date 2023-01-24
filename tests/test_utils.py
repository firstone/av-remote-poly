import utils


def test_simple(config_data):
    config = config_data['simple']
    utils.flatten_commands(config)
    assert len(list(config['commands'].keys())) == 2


def test_sub_group(config_data):
    config = config_data['sub_group']
    utils.flatten_commands(config)
    assert len(list(config['commands'].keys())) == 3


def test_no_main(config_data):
    config = config_data['no_main']
    utils.flatten_commands(config)
    assert len(list(config['commands'].keys())) == 1


def test_suffix(config_data):
    config = config_data['suffix']
    utils.flatten_commands(config)
    assert 'command1_g1' in config['commands']
    assert 'command2_g1' in config['commands']


def test_prefix(config_data):
    config = config_data['prefix']
    utils.flatten_commands(config)
    assert 'g1_command1' in config['commands']
    assert 'g1_command2' in config['commands']


def test_last_output_number(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['intCommand'], ['cmd123'], {}, '')
    assert output == '123'


def test_last_output_number_multi_line(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['intCommand'], ['cmd123', 'cmd234'], {}, '')
    assert output == '234'


def test_last_output_number_multi_prefix(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['intCommand'], ['cmd123', 'cmdn234'], {}, '')
    assert output == '123'


def test_last_output_float(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['floatCommand'], ['cmd123'], {}, '')
    assert output == '123'


def test_last_output_float_multi_line(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['floatCommand'], ['cmd123', 'cmd234'], {}, '')
    assert output == '234'


def test_last_output_hex(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['hexCommand'], ['cmdcaca'], {}, '')
    assert output == 'caca'


def test_last_output_hex_multi_line(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['hexCommand'], ['cmdbaba', 'cmdcaca'], {}, '')
    assert output == 'caca'


def test_last_output_values(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['valueCommand'], ['cmdkey1'], config['values'], '')
    assert output == 'key1'


def test_last_output_values_multi_line(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['valueCommand'], ['cmd123', 'cmdkey1'], config['values'], '')
    assert output == 'key1'


def test_last_output_suffix(config_data):
    config = config_data['last_output']
    output = utils.get_last_output(config['commands']['suffixCommand'], ['cmd123'], {}, 'n')
    assert output == '123'


def test_merge():
    d1 = {'a': {'b': {'c': {'val1': 1}}, 'd': 1}}

    d2 = {'a': {'b': {'c': {'val2': 2}}, 'e': 2}}

    utils.merge_objects(d1, d2)

    assert d1 == {'a': {'b': {'c': {'val1': 1, 'val2': 2}}, 'd': 1, 'e': 2}}
