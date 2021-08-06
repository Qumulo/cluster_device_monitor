#!/usr/bin/env python3
# Copyright (c) 2021 Qumulo, Inc. All rights reserved.
#
# NOTICE: All information and intellectual property contained herein is the
# confidential property of Qumulo, Inc. Reproduction or dissemination of the
# information or intellectual property contained herein is strictly forbidden,
# unless separate prior written permission has been obtained from Qumulo, Inc.

# TODO list....
# TODO: fix test for socket.timeout exception
# TODO: add tests for new QQ API exceptions changed in main'
# TODO: test credential failure
# TODO: add tests for EmailMessage.send()

import os
import unittest

from unittest import mock
from typing import Any, Dict

from cluster_device_monitor import (
    check_cluster_connectivity,
    check_for_unhealthy_objects,
    cluster_login,
    ConfigData,
    delete_previous_cluster_status,
    EmailMessage,
    generate_cluster_timeout_email,
    generate_event_alert_email,
    parse_config,
    populate_alert_email_body,
    preserve_cluster_status,
    qq_api_query,
    retrieve_status_of_cluster_devices,
    send_email,
)


CONFIG: Dict[str, Any] = {
    'cluster_settings': {
        'cluster_address': '10.120.0.34',
        'cluster_name': 'CoffeeTime',
        'username': 'admin',
        'password': 'Admin123',
        'rest_port': 8000,
    },
    'email_settings': {
        'sender': 'qumulo_event_alerts@qumulo.com',
        'server': 'mail.corp.qumulo.com',
        'mail_to': ['rthompson@qumulo.com'],
    },
}

CONFIG_DATA = ConfigData(
    '10.120.0.34',
    'CoffeeTime',
    'admin',
    'Admin123',
    8000,
    'qumulo_event_alerts@qumulo.com',
    'mail.corp.qumulo.com',
    ['rthompson@qumulo.com'],
)

EML = EmailMessage(CONFIG_DATA, 'subject', 'body')


class ParseConfigTest(unittest.TestCase):
    def test_default_config_loads(self) -> None:
        config = parse_config(CONFIG)
        self.assertEqual(
            CONFIG['cluster_settings']['cluster_address'], config.cluster_address
        )
        self.assertEqual(
            CONFIG['cluster_settings']['cluster_name'], config.cluster_name
        )
        self.assertEqual(CONFIG['cluster_settings']['username'], config.username)
        self.assertEqual(CONFIG['cluster_settings']['password'], config.password)
        self.assertEqual(CONFIG['cluster_settings']['rest_port'], config.rest_port)
        self.assertEqual(CONFIG['email_settings']['sender'], config.sender)
        self.assertEqual(CONFIG['email_settings']['server'], config.server)
        self.assertEqual(CONFIG['email_settings']['mail_to'], config.mail_to)

    def test_bad_config_raises_error(self) -> None:
        with self.assertRaisesRegex(SystemExit, 'Configuration element missing.'):
            _config = parse_config({'a': 'b'})


@mock.patch(
    'cluster_device_monitor.generate_cluster_timeout_email'
)
@mock.patch('cluster_device_monitor.socket')
class SocketConnectivityTest(unittest.TestCase):
    def test_socket_connectivity(
        self, _mock_socket: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        check_cluster_connectivity(CONFIG_DATA)
        mock_email.assert_not_called()

    def test_failed_socket_raises_error(
        self, mock_socket: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        mock_socket.socket.side_effect = Exception()
        check_cluster_connectivity(CONFIG_DATA)
        mock_email.assert_called_once()


class DeletePreviousStatusFileTest(unittest.TestCase):
    def test_file_does_not_exist(self) -> None:
        delete_previous_cluster_status()
        self.assertFalse('cluster_status_previous.json' in os.listdir())


@mock.patch(
    'cluster_device_monitor.generate_cluster_timeout_email'
)
@mock.patch('cluster_device_monitor.RestClient')
class ClusterLoginTest(unittest.TestCase):
    def test_cluster_login(
        self, _mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _return = cluster_login(CONFIG_DATA)
        mock_email.assert_not_called()

    def test_cluster_failed_login_raises_error(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        mock_rest.side_effect = Exception()
        _response = cluster_login(CONFIG_DATA)
        mock_email.assert_called_once()


@mock.patch(
    'cluster_device_monitor.generate_cluster_timeout_email'
)
@mock.patch('cluster_device_monitor.RestClient')
class QQApiQueriesTest(unittest.TestCase):
    def test_get_cluster_name(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _response = qq_api_query(mock_rest, CONFIG_DATA, 'cluster_name')
        mock_email.assert_not_called()

    def test_get_cluster_version(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _response = qq_api_query(mock_rest, CONFIG_DATA, 'qq_version')
        mock_email.assert_not_called()

    def test_get_cluster_time(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _response = qq_api_query(mock_rest, CONFIG_DATA, 'cluster_time')
        mock_email.assert_not_called()

    def test_get_cluster_uuid(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _response = qq_api_query(mock_rest, CONFIG_DATA, 'cluster_uuid')
        mock_email.assert_not_called()

    def test_api_timeout_raises_error(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        mock_rest.cluster.get_cluster_conf.side_effect = Exception()
        qq_api_query(mock_rest, CONFIG_DATA, 'cluster_name')
        mock_email.assert_called_once()


@mock.patch(
    'cluster_device_monitor.generate_cluster_timeout_email'
)
@mock.patch('cluster_device_monitor.RestClient')
class RetrieveStatusOfClusterDevicesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_node_real_dict = {
            'id': 1,
            'node_status': 'online',
            'node_name': 'CoffeeTime-1',
            'model_number': 'QVIRT',
            'serial_number': 'QVIRT',
        }
        self.sample_drive_real_dict = {
            'id': '1.1',
            'node_id': 1,
            'slot': 1,
            'state': 'healthy',
            'disk_type': 'SSD',
            'disk_model': 'Virtual_disk',
            'disk_serial_number': '',
            'capacity': '10467934208',
        }

    def test_retrieve_status_of_nodes(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        expected = {
            'id': 1,
            'node_status': 'online',
            'node_name': 'CoffeeTime-1',
            'model_number': 'QVIRT',
            'serial_number': 'QVIRT',
        }
        mock_rest.cluster.list_nodes.return_value = [self.sample_node_real_dict]
        status_of_nodes = retrieve_status_of_cluster_devices(
            mock_rest, CONFIG_DATA, 'nodes'
        )
        self.assertEqual(status_of_nodes['nodes'][0], expected)
        expected['node_status'] = 'offline'
        status_of_nodes['nodes'][0]['node_status'] = 'offline'
        self.assertEqual(status_of_nodes['nodes'][0], expected)
        mock_email.assert_not_called()

    def test_retrieve_status_of_drives(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        expected = {
            'id': '1.1',
            'node_id': 1,
            'slot': 1,
            'state': 'healthy',
            'disk_type': 'SSD',
            'disk_model': 'Virtual_disk',
            'disk_serial_number': '',
            'capacity': '10467934208',
        }
        mock_rest.cluster.get_cluster_slots_status.return_value = [
            self.sample_drive_real_dict
        ]
        status_of_drives = retrieve_status_of_cluster_devices(
            mock_rest, CONFIG_DATA, 'drives'
        )
        self.assertEqual(status_of_drives['drives'][0], expected)
        expected['state'] = 'unhealthy'
        status_of_drives['state'] = 'unhealthy'
        status_of_drives['drives'][0]['state'] = 'unhealthy'
        self.assertEqual(status_of_drives['drives'][0], expected)
        mock_email.assert_not_called()

    def test_api_timeout_raises_error(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        mock_rest.cluster.list_nodes.side_effect = Exception()
        retrieve_status_of_cluster_devices(mock_rest, CONFIG_DATA, 'nodes')
        mock_email.assert_called_once()


class PreserveClusterStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cluster_status = {
            'nodes': [
                {
                    'id': 1,
                    'node_status': 'online',
                    'node_name': 'CoffeeTime-1',
                    'uuid': '10a1c7aa-fb99-48a1-8dc3-b34b96777742',
                    'label': '00:50:56:bf:68:82',
                    'model_number': 'QVIRT',
                    'serial_number': 'QVIRT',
                    'mac_address': '00:50:56:bf:68:82',
                }
            ],
            'drives': [
                {
                    'id': '1.1',
                    'node_id': 1,
                    'slot': 1,
                    'state': 'healthy',
                    'slot_type': 'SSD',
                    'disk_type': 'SSD',
                    'disk_model': 'Virtual_disk',
                    'disk_serial_number': '1234',
                    'capacity': '10467934208',
                    'raw_capacity': '10737418240',
                    'minimum_raw_capacity': '10737418240',
                    'high_endurance': False,
                    'drive_bay': '',
                    'led_pattern': 'LED_PATTERN_NORMAL',
                }
            ],
        }

    def test_cluster_status_file_created_and_populated(self) -> None:
        preserve_cluster_status(self.cluster_status)
        self.assertIn('cluster_status.json', os.listdir())
        self.assertEqual(self.cluster_status['nodes'][0]['id'], 1)
        self.assertEqual(self.cluster_status['nodes'][0]['node_status'], 'online')
        self.assertEqual(self.cluster_status['nodes'][0]['model_number'], 'QVIRT')
        self.assertEqual(self.cluster_status['nodes'][0]['serial_number'], 'QVIRT')
        self.assertEqual(self.cluster_status['drives'][0]['id'], '1.1')
        self.assertEqual(self.cluster_status['drives'][0]['node_id'], 1)
        self.assertEqual(self.cluster_status['drives'][0]['slot'], 1)
        self.assertEqual(self.cluster_status['drives'][0]['state'], 'healthy')
        self.assertEqual(self.cluster_status['drives'][0]['disk_type'], 'SSD')
        self.assertEqual(self.cluster_status['drives'][0]['disk_model'], 'Virtual_disk')
        self.assertEqual(self.cluster_status['drives'][0]['disk_serial_number'], '1234')
        self.assertEqual(self.cluster_status['drives'][0]['capacity'], '10467934208')

    def tearDown(self) -> None:
        os.remove('cluster_status.json')
        self.assertTrue('cluster_status.json' not in os.listdir())


class CheckForUnhealthyObjectsTest(unittest.TestCase):
    def test_healthy_nodes_returns_no_alerts(self) -> None:
        status: Dict[str, Any] = {'nodes': [{'node_status': 'online'}], 'drives': []}
        alert_data, healthy = check_for_unhealthy_objects(status)
        self.assertEqual(alert_data, {})
        self.assertTrue(healthy)

    def test_healthy_drives_returns_no_alerts(self) -> None:
        status: Dict[str, Any] = {'nodes': [], 'drives': [{'state': 'healthy'}]}
        alert_data, healthy = check_for_unhealthy_objects(status)
        self.assertEqual(alert_data, {})
        self.assertTrue(healthy)

    def test_unhealthy_node_returns_alert(self) -> None:
        status: Dict[str, Any] = {'nodes': [{'node_status': 'offline'}], 'drives': []}
        alert_data, healthy = check_for_unhealthy_objects(status)
        self.assertEqual(alert_data, {'Event 1': status['nodes'][0]})
        self.assertFalse(healthy)

    def test_unhealthy_drive_returns_alert(self) -> None:
        status: Dict[str, Any] = {'nodes': [], 'drives': [{'state': 'missing'}]}
        alert_data, healthy = check_for_unhealthy_objects(status)
        self.assertEqual(alert_data, {'Event 1': status['drives'][0]})
        self.assertFalse(healthy)

    def test_unhealthy_node_and_drive_returns_alert(self) -> None:
        status = {
            'nodes': [{'node_status': 'offline'}],
            'drives': [{'state': 'missing'}],
        }
        alert_data, healthy = check_for_unhealthy_objects(status)
        self.assertEqual(
            alert_data, {'Event 1': status['nodes'][0], 'Event 2': status['drives'][0]}
        )
        self.assertFalse(healthy)


@mock.patch(
    'cluster_device_monitor.generate_cluster_timeout_email'
)
@mock.patch('cluster_device_monitor.RestClient')
class BuildEmailTest(unittest.TestCase):
    def setUp(self) -> None:
        self.alert_data = {
            'Event 1': {
                'id': 2,
                'node_status': 'offline',
                'node_name': 'CoffeeTime-2',
                'uuid': 'cbdea0e3-1659-48af-b15b-e97dbbeefd04',
                'label': '00:50:56:bf:f1:57',
                'model_number': 'QVIRT',
                'serial_number': '',
                'mac_address': '',
            }
        }
        self.qq_version = '4.1.0'
        self.cluster_name = 'CoffeeTime'
        self.cluster_uuid = 'cf83e828-7ef7-4368-a75b-3b972d10f2c6'  # len() = 36
        self.cluster_time = '2021-07-23T17:35:29.189487278Z UTC'  # len() = 34

    def test_qq_api_query_success(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        _email_alert = populate_alert_email_body(
            self.alert_data, mock_rest, CONFIG_DATA
        )
        mock_email.assert_not_called()

    def test_qq_api_query_timeout_raises_error(
        self, mock_rest: mock.MagicMock, mock_email: mock.MagicMock
    ) -> None:
        mock_rest.cluster.get_cluster_conf.side_effect = Exception()
        _email_alert = populate_alert_email_body(
            self.alert_data, mock_rest, CONFIG_DATA
        )
        mock_email.assert_called_once()

    def test_email_contains_alert_data(
        self, mock_rest: mock.MagicMock, _mock_email: mock.MagicMock
    ) -> None:
        email_alert = populate_alert_email_body(self.alert_data, mock_rest, CONFIG_DATA)
        self.assertIn(str(self.alert_data['Event 1']['id']), email_alert)
        self.assertIn(self.alert_data['Event 1']['node_status'], email_alert)
        self.assertIn(self.alert_data['Event 1']['serial_number'], email_alert)
        self.assertIn(self.alert_data['Event 1']['model_number'], email_alert)


@mock.patch('cluster_device_monitor.smtplib')
class SendEmailTest(unittest.TestCase):
    def test_can_send_email(self, _mock_smtp: mock.MagicMock) -> None:
        send_email(EML)


@mock.patch('cluster_device_monitor.send_email')
class GenerateEventAlertEmailTest(unittest.TestCase):
    def test_send_email_success(self, mock_send_email: mock.MagicMock) -> None:
        generate_event_alert_email(CONFIG_DATA, 'foo')
        mock_send_email.assert_called_once()

    def test_send_email_failure_raises_error(
        self, mock_send_email: mock.MagicMock
    ) -> None:
        mock_send_email.side_effect = Exception()
        with self.assertRaisesRegex(SystemExit, 'Check connection to SMTP server.'):
            generate_event_alert_email(CONFIG_DATA, 'foo')


@mock.patch('cluster_device_monitor.send_email')
class GenerateTimeoutAlertEmailTest(unittest.TestCase):
    def setUp(self) -> None:
        self.error = 'Error 403: Access Denied.'

    def test_send_email_success(self, mock_send_email: mock.MagicMock) -> None:
        with self.assertRaisesRegex(SystemExit, 'EMAIL SENT'):
            generate_cluster_timeout_email(self.error, CONFIG_DATA)
        mock_send_email.assert_called_once()

    def test_send_email_failure_raises_error(
        self, mock_send_email: mock.MagicMock
    ) -> None:
        mock_send_email.side_effect = Exception()
        with self.assertRaisesRegex(SystemExit, 'Unable to send email.'):
            generate_cluster_timeout_email(self.error, CONFIG_DATA)


if __name__ == '__main__':
    unittest.main()
