#!/usr/bin/python3

import os


class TestLibhaproxy():

    def test_pytest(self):
        assert True

    def test_ph(self, ph):
        ''' See if the ph fixture works to load charm configs '''
        assert isinstance(ph.charm_config, dict)

    def test_proxy_config(self, ph):
        ''' Check that default proxy config can be read '''
        default_options = [('httplog', ''), ('dontlognull', '')]
        for option in ph.proxy_config.defaults[0].options():
            assert option in default_options

    def test_add_timeout_tunnel(self, ph):
        test_options = [('tunnel timeout 1h', '')]
        for option in ph.proxy_config.defaults[0].options():
            assert option not in test_options
        ph.add_timeout_tunnel()
        for option in ph.proxy_config.defaults[0].options():
            if option in test_options:
                break
            else:
                continue
            assert 0  # test_options not found in default section

    def test_get_config_names(self, ph, mock_remote_unit):
        config = {'group_id': 'test_group'}
        remote_unit, backend_name = ph.get_config_names(config)

    def test_process_config(self, ph, monkeypatch):
        # Test writting a config file
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        assert ph.process_config(config)['cfg_good'] is True

        # Error if tcp requested on existing http frontend
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/1')
        config['mode'] = 'tcp'
        assert ph.process_config(config)['cfg_good'] is False

        # Successful tcp on unused frontend
        config['external_port'] = 90
        assert ph.process_config(config)['cfg_good'] is True

        # Error if http requested on existing tcp frontend
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/2')
        config['mode'] = 'http'
        assert ph.process_config(config)['cfg_good'] is False

        # Register with subdomain
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/2')
        config['subdomain'] = 'subtest'
        config['external_port'] = 80
        assert ph.process_config(config)['cfg_good'] is True

        # Register with only subdomain
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/3')
        config['urlbase'] = None
        assert ph.process_config(config)['cfg_good'] is True

        # Add two units with a group-id
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/4')
        config['group_id'] = 'test-group'
        assert ph.process_config(config)['cfg_good'] is True
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/5')
        config['group_id'] = 'test-group'
        assert ph.process_config(config)['cfg_good'] is True

        # Check that the expected number of backends are in use
        # Backends 0,2,3,4,5 should be in use by HTTP
        http_fe = ph.get_frontend(80, create=False)
        assert len(http_fe.config_block['usebackends']) == 5

    def test_get_frontend(self, ph):
        import pyhaproxy
        assert ph.get_frontend(80, create=False) is None
        assert not isinstance(ph.get_frontend(80, create=False), pyhaproxy.config.Frontend)
        assert isinstance(ph.get_frontend(80), pyhaproxy.config.Frontend)
        assert isinstance(ph.get_frontend(80, create=False), pyhaproxy.config.Frontend)
        assert ph.get_frontend(70).port == '70'
        assert ph.get_frontend(80).port == '80'
        assert ph.get_frontend(90).port == '90'

    def test_get_backend(self, ph, monkeypatch):
        import pyhaproxy
        # Create and return a new backend
        new_be = ph.get_backend('test-backend')
        assert isinstance(new_be, pyhaproxy.config.Backend)
        assert new_be.name == 'test-backend'
        assert new_be.config_block['configs'] == []
        # Retrieve existing backend
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        ph.process_config(config)
        backend = ph.get_backend('unit-mock-0')
        assert backend.name == 'unit-mock-0'
        assert backend.config_block['configs'] != []

    def test_enable_stats(self, ph):
        # Can't enable if FE is in use
        fe9000 = ph.get_frontend(9000)
        assert fe9000.port == '9000'
        assert fe9000.name == 'relation-9000'
        assert ph.enable_stats() is False
        # Can enable if FE is available
        fe9000.port = 0
        assert ph.enable_stats() is True
        festats = ph.get_frontend(9000)
        assert festats.name == 'stats'

    def test_disable_sats(self, ph):
        # 9k FE is Stats after enable
        assert ph.enable_stats() is True
        fe9000 = ph.get_frontend(9000)
        assert fe9000.name == 'stats'
        # 9k FE is not Stats after disable
        ph.disable_stats()
        fe9000 = ph.get_frontend(9000)
        assert fe9000.name == 'relation-9000'

    def test_available_fort_http(self, ph, monkeypatch):
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        # Create http at 80
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        assert ph.process_config(config)['cfg_good'] is True
        fe80 = ph.get_frontend(80)
        # Create tcp at 90
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/1')
        config['mode'] = 'tcp'
        config['external_port'] = 90
        assert ph.process_config(config)['cfg_good'] is True
        fe90 = ph.get_frontend(90)
        # Get default stats frontend
        fe9000 = ph.get_frontend(9000)
        # Verify http checks
        assert ph.available_for_http(fe80) is True
        assert ph.available_for_http(fe90) is False
        # Check stats port
        assert ph.available_for_http(fe9000) is True
        fe9000.port = 0  # Move from 9k so stats can enable
        ph.enable_stats()
        fe9000 = ph.get_frontend(9000)
        assert ph.available_for_http(fe9000) is False

    def test_available_fort_tcp(self, ph, monkeypatch):
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        # Create http at 80
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        assert ph.process_config(config)['cfg_good'] is True
        fe80 = ph.get_frontend(80)
        # Create tcp at 90
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/1')
        config['mode'] = 'tcp'
        config['external_port'] = 90
        assert ph.process_config(config)['cfg_good'] is True
        fe90 = ph.get_frontend(90)
        # Get default stats frontend
        fe9000 = ph.get_frontend(9000)
        # Verify tcp checks
        assert ph.available_for_tcp(fe80, 'unit-mock-0') is False
        assert ph.available_for_tcp(fe90, 'unit-mock-0') is False
        assert ph.available_for_tcp(fe90, 'unit-mock-1') is True
        # Check stats port
        assert ph.available_for_tcp(fe9000, 'unit-mock-0') is True
        assert ph.available_for_tcp(fe9000, 'unit-mock-1') is True
        fe9000.port = 0  # Move from 9k so stats can enable
        ph.enable_stats()
        fe9000 = ph.get_frontend(9000)
        assert ph.available_for_tcp(fe9000, 'unit-mock-0') is False
        assert ph.available_for_tcp(fe9000, 'unit-mock-1') is False

    def test_clean_config(self, ph, monkeypatch):
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        # Test adding and removing single unit
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        remote_unit, backend_name = ph.get_config_names(config)
        ph.process_config(config)
        assert ph.get_frontend(80, create=False) is not None
        ph.clean_config(remote_unit, backend_name)
        assert ph.get_frontend(80, create=False) is None
        # Setup mulpitle units to test with
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        assert ph.process_config(config)['cfg_good'] is True
        unit_0, backend_0 = ph.get_config_names(config)
        ph.process_config(config)

        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/1')
        unit_1, backend_1 = ph.get_config_names(config)
        ph.process_config(config)

        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/2')
        config['group_id'] = 'test-group'
        unit_2, backend_2 = ph.get_config_names(config)
        ph.process_config(config)

        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/3')
        unit_3, backend_3 = ph.get_config_names(config)
        ph.process_config(config)
        assert backend_2 == backend_3

        assert ph.get_frontend(80, create=False) is not None
        fe = ph.get_frontend(80, create=False)
        assert len(fe.config_block['usebackends']) == 4
        assert ph.get_backend(backend_0, create=False) is not None
        assert ph.get_backend(backend_1, create=False) is not None
        assert ph.get_backend(backend_2, create=False) is not None
        assert ph.get_backend(backend_3, create=False) is not None

        # Remove 1 of the grouped backends and re-check
        ph.clean_config(unit_3, backend_3)
        assert len(fe.config_block['usebackends']) == 3
        assert ph.get_backend(backend_0, create=False) is not None
        assert ph.get_backend(backend_1, create=False) is not None
        assert ph.get_backend(backend_2, create=False) is not None
        assert ph.get_backend(backend_3, create=False) is not None

        # Remove the other and check that the group is now gone
        ph.clean_config(unit_2, backend_2)
        assert len(fe.config_block['usebackends']) == 2
        assert ph.get_backend(backend_0, create=False) is not None
        assert ph.get_backend(backend_1, create=False) is not None
        assert ph.get_backend(backend_2, create=False) is None
        assert ph.get_backend(backend_3, create=False) is None

        # Remove another backend
        ph.clean_config(unit_1, backend_1)
        assert len(fe.config_block['usebackends']) == 1
        assert ph.get_backend(backend_0, create=False) is not None
        assert ph.get_backend(backend_1, create=False) is None
        assert ph.get_backend(backend_2, create=False) is None
        assert ph.get_backend(backend_3, create=False) is None

        # Remove final backend and frontend
        ph.clean_config(unit_0, backend_0)
        assert ph.get_backend(backend_0, create=False) is None
        assert ph.get_backend(backend_1, create=False) is None
        assert ph.get_backend(backend_2, create=False) is None
        assert ph.get_backend(backend_3, create=False) is None

    def test_save_config(self, ph, monkeypatch):
        import os
        initial_time = os.path.getmtime(ph.proxy_config_file)
        # Modify config should change mtime
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        ph.process_config(config)
        time2 = os.path.getmtime(ph.proxy_config_file)
        assert initial_time != time2

    def test_update_ports(self, ph, monkeypatch):
        import sys
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        mports = sys.modules['libhaproxy'].subprocess.check_output
        # Check that ports start empty and dont' change on update_ports
        assert mports.open_ports == ''
        ph.update_ports()
        assert mports.open_ports == ''
        # Ading a port opens it
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        unit_0, backend_0 = ph.get_config_names(config)
        ph.process_config(config)
        ph.update_ports()
        assert mports.open_ports == '80/tcp\n'
        # Duplicate ports aren't added
        ph.get_frontend(80)
        ph.update_ports()
        assert mports.open_ports == '80/tcp\n'
        # If ports are removed, they get added back
        mports.open_ports = ''
        ph.update_ports()
        assert mports.open_ports == '80/tcp\n'
        # If a frontend is removed, so is the port
        ph.clean_config(unit_0, backend_0)
        assert mports.open_ports == ''
        # Close stats port if open during update
        ph.charm_config['enable-stats'] = True
        ph.enable_stats()
        assert mports.open_ports == ''
        print(mports.open_ports)
        ph.update_ports()
        print(mports.open_ports)
        assert mports.open_ports == ''

    def test_merge_letsencrypt_cert(self, ph, cert):
        assert not os.path.isfile(ph.cert_file)
        ph.merge_letsencrypt_cert()
        assert os.path.isfile(ph.cert_file)
        with open(ph.cert_file, 'r') as cert_file:
            assert cert_file.readline() == 'fullchain.pem\n'
            assert cert_file.readline() == 'privkey.pem\n'

    def test_add_cron(self, ph, mock_crontab):
        action = 'test-action'
        interval = 'test-interval'
        # Collect CronTab calls from add and remove
        ph.add_cron(action, interval)
        ph.remove_cron(action)
        calls = {}
        for call in mock_crontab.mock_calls:
            name, args, kwargs = call
            calls[name] = {'args': args, 'kwargs': kwargs}

        # Check add cron calls CronTab with expected action and interval
        assert calls['().new']['kwargs']['command'].split('/')[-1] == action
        assert interval in calls['().new().setall']['args']
        # Check that add and remove use same comment
        assert calls['().new']['kwargs']['comment'] == calls['().find_comment']['args'][0]

    def test_cert_cron(self, ph, mock_crontab):
        action = 'renew-cert'
        interval = '@daily'
        ph.add_cert_cron()
        ph.remove_cert_cron()
        calls = {}
        for call in mock_crontab.mock_calls:
            name, args, kwargs = call
            calls[name] = {'args': args, 'kwargs': kwargs}

        # Check add cron calls CronTab with expected action and interval
        assert calls['().new']['kwargs']['command'].split('/')[-1] == action
        assert interval in calls['().new().setall']['args']
        # Check that add and remove use same comment
        assert calls['().new']['kwargs']['comment'] == calls['().find_comment']['args'][0]

    def test_upnp_cron(self, ph, mock_crontab):
        action = 'renew-upnp'
        interval = '@hourly'
        ph.add_upnp_cron()
        ph.remove_upnp_cron()
        calls = {}
        for call in mock_crontab.mock_calls:
            name, args, kwargs = call
            calls[name] = {'args': args, 'kwargs': kwargs}

        # Check add cron calls CronTab with expected action and interval
        assert calls['().new']['kwargs']['command'].split('/')[-1] == action
        assert interval in calls['().new().setall']['args']
        # Check that add and remove use same comment
        assert calls['().new']['kwargs']['comment'] == calls['().find_comment']['args'][0]

    def test_enable_letsencrypt(self, ph, cert, mock_crontab):
        ph.enable_letsencrypt()
        fe80 = ph.get_frontend(80, create=False)
        fe443 = ph.get_frontend(443, create=False)
        assert fe80.config_block['acls'][0].name == 'letsencrypt'
        assert fe80.config_block['usebackends'][0].backend_name == 'letsencrypt-backend'
        assert 'mock.pem' in fe443.config_block['binds'][0].attributes[0]
        assert fe443.config_block['acls'][0].name == 'letsencrypt'
        assert fe443.config_block['usebackends'][0].backend_name == 'letsencrypt-backend'
        assert 'reqirep' in fe443.config_block['configs'][0][0]

    def test_disable_letsencrypt(self, ph, cert, mock_crontab, monkeypatch):
        # Remove letsencrypt and all unused sections
        ph.enable_letsencrypt()
        assert ph.get_frontend(80, create=False) is not None
        assert ph.get_frontend(443, create=False) is not None
        assert ph.get_backend('letsencrypt-backend', create=False) is not None
        ph.disable_letsencrypt()
        assert ph.get_frontend(80, create=False) is None
        assert ph.get_frontend(443, create=False) is None
        assert ph.get_backend('letsencrypt-backend', create=False) is None

        # Remove letsencrypt but not other frontends
        ph.enable_letsencrypt()
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')
        ph.process_config(config)
        monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/1')
        config['external_port'] = 443
        ph.process_config(config)
        ph.disable_letsencrypt()
        fe80 = ph.get_frontend(80, create=False)
        fe443 = ph.get_frontend(443, create=False)
        assert fe80.config_block['acls'][0].name == 'unit-mock-0'
        assert fe80.config_block['usebackends'][0].backend_name == 'unit-mock-0'
        assert fe443.config_block['binds'][0].attributes == []
        assert fe443.config_block['acls'][0].name == 'unit-mock-1'
        assert fe443.config_block['usebackends'][0].backend_name == 'unit-mock-1'
        assert fe443.config_block['configs'] == []
        assert ph.get_backend('letsencrypt-backend', create=False) is None

    def test_renew_cert(self, ph, monkeypatch):
        import mock
        mocks = {'disable': mock.Mock(), 'enable': mock.Mock(), 'renew':
                 mock.Mock(), 'merge': mock.Mock()}
        monkeypatch.setattr(ph, 'disable_letsencrypt', mocks['disable'])
        monkeypatch.setattr(ph, 'enable_letsencrypt', mocks['enable'])
        monkeypatch.setattr('libhaproxy.letsencrypt.renew', mocks['renew'])
        monkeypatch.setattr(ph, 'merge_letsencrypt_cert', mocks['merge'])
        assert mocks['disable'].call_count == 0
        assert mocks['enable'].call_count == 0
        assert mocks['renew'].call_count == 0
        assert mocks['merge'].call_count == 0
        ph.renew_cert()
        assert mocks['disable'].call_count == 1
        assert mocks['enable'].call_count == 1
        assert mocks['renew'].call_count == 0
        assert mocks['merge'].call_count == 0
        ph.renew_cert(full=False)
        assert mocks['disable'].call_count == 1
        assert mocks['enable'].call_count == 1
        assert mocks['renew'].call_count == 1
        assert mocks['merge'].call_count == 1

    def test_renew_upnp(self, ph):
        import mock
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.renew_upnp()
            assert mockports.call_count == 0
        ph.get_frontend(80)
        ph.get_frontend(90)
        ph.update_ports()
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.renew_upnp()
            assert mockports.call_count == 2
        ph.get_frontend(8080)
        ph.update_ports()
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.renew_upnp()
            assert mockports.call_count == 3

    def test_release_upnp(self, ph):
        import mock
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.release_upnp()
            assert mockports.call_count == 0
        ph.get_frontend(80)
        ph.get_frontend(90)
        ph.update_ports()
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.release_upnp()
            assert mockports.call_count == 2
        ph.get_frontend(8080)
        ph.update_ports()
        with mock.patch('libhaproxy.subprocess.check_call') as mockports:
            ph.release_upnp()
            assert mockports.call_count == 3
