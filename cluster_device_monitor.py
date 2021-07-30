#!/usr/bin/env python3
# Copyright (c) 2021 Qumulo, Inc. All rights reserved.
#
# NOTICE: All information and intellectual property contained herein is the
# confidential property of Qumulo, Inc. Reproduction or dissemination of the
# information or intellectual property contained herein is strictly forbidden,
# unless separate prior written permission has been obtained from Qumulo, Inc.

"""
cluster_device_monitor.py interacts with the Qumulo Rest API to retrieve the
status of NODES and DRIVES. The cluster response data is recorded into
cluster_status.json, which is used to parse through for unhealthy nodes and
drives. If unhealthy objects are found, an email will be sent to all addresses
defined in the 'mail_to' key of the config.json file.

cluster_device_monitor.py has logic to look for previous iterations of the
script being ran and will not send email alerts if the alerts were previously
generated & sent. The script also contains logic to send an email alert if it
loses connection with the API or fails to log into the cluster.
"""


import argparse
import json
import os
import smtplib
import socket
import sys

from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Sequence, Tuple

from qumulo.rest_client import RestClient

#   ____ _        _    ____ ____  _____ ____
#  / ___| |      / \  / ___/ ___|| ____/ ___|
# | |   | |     / _ \ \___ \___ \|  _| \___ \
# | |___| |___ / ___ \ ___) |__) | |___ ___) |
#  \____|_____/_/   \_\____/____/|_____|____/


class ConfigData:
    """
    Data for config file.
    """
    cluster_address: str
    cluster_name: str
    username: str
    password: str
    rest_port: int
    sender: str
    server: str
    mail_to: List[str]

    def __init__(
        self,
        cluster_address: str,
        cluster_name: str,
        username: str,
        password: str,
        rest_port: int,
        sender: str,
        server: str,
        mail_to: List[str]
    ):
        self.cluster_address = cluster_address
        self.cluster_name = cluster_name
        self.username = username
        self.password = password
        self.rest_port = rest_port
        self.sender = sender
        self.server = server
        self.mail_to = mail_to


class EmailMessage:
    """
    Data for email message.
    """
    config: 'ConfigData'
    subject: str
    body: str

    def __init__(
        self,
        config: 'ConfigData',
        subject: str,
        body: str
    ):
        self.config = config
        self.subject = subject
        self.body = body


#  _   _ _____ _     ____  _____ ____  ____
# | | | | ____| |   |  _ \| ____|  _ \/ ___|
# | |_| |  _| | |   | |_) |  _| | |_) \___ \
# |  _  | |___| |___|  __/| |___|  _ < ___) |
# |_| |_|_____|_____|_|   |_____|_| \_\____/


def parse_config(config_file: Dict[str, Any]) -> 'ConfigData':
    """
    Extract values from the config file.
    """
    try:
        cluster_address = config_file['cluster_settings']['cluster_address']
        cluster_name = config_file['cluster_settings']['cluster_name']
        username = config_file['cluster_settings']['username']
        password = config_file['cluster_settings']['password']
        rest_port = int(config_file['cluster_settings']['rest_port'])

        sender = config_file['email_settings']['sender']
        server = config_file['email_settings']['server']
        mail_to = config_file['email_settings']['mail_to']
    except Exception as err:
        sys.exit(f'ERROR: {err}\nConfiguration element missing. Exiting...')

    return ConfigData(
        cluster_address,
        cluster_name,
        username,
        password,
        rest_port,
        sender,
        server,
        mail_to,
    )


def load_json(config_path: str) -> Dict[str, Any]:
    """
    Try to load a JSON file.
    """
    try:
        with open(config_path, 'r') as file:
            return json.load(file)
    except ValueError as err:
        sys.exit(f'ERROR: {err}\nInvalid JSON file: {config_path}. Exiting...')


def load_and_parse_config(config_path: str) -> 'ConfigData':
    """
    Load config JSON file and record information.
    """
    try:
        config_file = load_json(config_path)
        return parse_config(config_file)
    except Exception as err:
        sys.exit(f'ERROR: {err}\nUnable to load or parse config. Exiting...')


def check_cluster_connectivity(config_data: 'ConfigData') -> None:
    """
    Verify that we can communicate to the cluster over the REST port.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((config_data.cluster_address, config_data.rest_port))
        sock.shutdown(socket.SHUT_WR)
        sock.close()
    except Exception as err:
        generate_cluster_timeout_email(str(err), config_data)


def delete_previous_cluster_status() -> None:
    """
    Delete cluster_status_previous.json if it exists.
    """
    if 'cluster_status_previous.json' in os.listdir():
        os.remove('cluster_status_previous.json')


#   ___  _   _ _____ ______   __     _    ____ ___
#  / _ \| | | | ____|  _ \ \ / /    / \  |  _ \_ _|
# | | | | | | |  _| | |_) \ V /    / _ \ | |_) | |
# | |_| | |_| | |___|  _ < | |    / ___ \|  __/| |
#  \__\_\\___/|_____|_| \_\|_|___/_/   \_\_|  |___|
#


def cluster_login(config_data: 'ConfigData') -> Optional[RestClient]:
    """
    Log into cluster via Qumulo Rest API.
    """
    rest_client = None
    try:
        rest_client = RestClient(config_data.cluster_address, config_data.rest_port)
        rest_client.login(config_data.username, config_data.password)
    except Exception as err:
        generate_cluster_timeout_email(str(err), config_data)

    return rest_client


def qq_api_query(
    rest_client: RestClient, config_data: 'ConfigData', api_call: str
) -> Optional[str]:
    """
    Query Qumulo via Qumulo REST API for cluster information based on api_call.
    """
    response = None

    try:
        if api_call == 'cluster_name':
            response = rest_client.cluster.get_cluster_conf()['cluster_name']
        elif api_call == 'qq_version':
            response = rest_client.version.version()['revision_id']
        elif api_call == 'cluster_time':
            response = rest_client.time_config.get_time_status()['time']
        elif api_call == 'cluster_uuid':
            response = rest_client.node_state.get_node_state()['cluster_id']
    except Exception as err:
        generate_cluster_timeout_email(str(err), config_data)

    return response


def retrieve_status_of_cluster_devices(
    rest_client: RestClient, config_data: 'ConfigData', device_type: str
) -> Dict[str, Any]:
    """
    API Query: Retrieve statuses of specified cluster devices // Data parsing
    """
    status_of_devices = {}

    try:
        if device_type == 'nodes':
            status_of_devices['nodes'] = rest_client.cluster.list_nodes()
        elif device_type == 'drives':
            status_of_devices['drives'] = rest_client.cluster.get_cluster_slots_status()
    except Exception as err:
        generate_cluster_timeout_email(str(err), config_data)

    return status_of_devices


#  ____  _______     _____ _______        __       ____    _  _____  _
# |  _ \| ____\ \   / /_ _| ____\ \      / /      |  _ \  / \|_   _|/ \
# | |_) |  _|  \ \ / / | ||  _|  \ \ /\ / /       | | | |/ _ \ | | / _ \
# |  _ <| |___  \ V /  | || |___  \ V  V /        | |_| / ___ \| |/ ___ \
# |_| \_\_____|  \_/  |___|_____|  \_/\_/____ ____|____/_/   \_\_/_/   \_\
#                                      |_____|_____|


def preserve_cluster_status(cluster_status: Dict[str, Any]) -> None:
    """
    Preserve the previous cluster status if it exists, and create new cluster status JSON file.
    """
    if 'cluster_status.json' in os.listdir():
        os.rename('cluster_status.json', 'cluster_status_previous.json')
    with open('cluster_status.json', 'w') as file:
        json.dump(cluster_status, file, indent=4)


def check_for_unhealthy_objects(cluster_status: Dict[str, Any]) -> Tuple[dict, bool]:
    """
    Parse through cluster_state.json for unhealthy objects.
    """
    nodes = cluster_status['nodes']
    drives = cluster_status['drives']
    alert_data = {}
    healthy = True
    counter = 1

    # scan through JSON for offline nodes
    for node in nodes:
        if node['node_status'] != 'online':
            alert_data[f'Event {counter}'] = node
            counter += 1
            healthy = False
    # scan through JSON for unhealthy drives
    for drive in drives:
        if drive['state'] != 'healthy':
            alert_data[f'Event {counter}'] = drive
            counter += 1
            healthy = False

    return alert_data, healthy


#  _____ __  __    _    ___ _     ___ _   _  ____
# | ____|  \/  |  / \  |_ _| |   |_ _| \ | |/ ___|
# |  _| | |\/| | / _ \  | || |    | ||  \| | |  _
# | |___| |  | |/ ___ \ | || |___ | || |\  | |_| |
# |_____|_|  |_/_/   \_\___|_____|___|_| \_|\____|


def populate_alert_email_body(
    alert_data: Dict[str, Any], rest_client: RestClient, config_data: 'ConfigData'
) -> str:
    """
    Generate email body for alert information.
    """
    qq_version = qq_api_query(rest_client, config_data, 'qq_version')
    cluster_name = qq_api_query(rest_client, config_data, 'cluster_name')
    cluster_uuid = qq_api_query(rest_client, config_data, 'cluster_uuid')
    cluster_time = qq_api_query(rest_client, config_data, 'cluster_time')

    alert_header = '=' * 19 + '<b> CLUSTER EVENT ALERT! </b>' + '=' * 19
    node_event_heading = '=' * 23 + '<b> NODE OFFLINE </b>' + '=' * 23
    drive_event_heading = '=' * 21 + '<b> DRIVE UNHEALTHY </b>' + '=' * 21
    email_alert = (
        f'{alert_header}\nUnhealthy object(s) found. See below for '
        'info and engage Qumulo Support in your preferred fashion.\n'
        f'Cluster name: {cluster_name}\n'
        f'Cluster UUID: {cluster_uuid}\n'
        f'Approx. time: {cluster_time} UTC\n'
        f'Qumulo Core Version: {qq_version}\n\n'
        f'<i>{len(alert_data)} Event(s) found:</i>\n'
    )

    for entry in alert_data:
        for key in alert_data[entry].keys():
            if key == 'node_status':  # node alert
                email_alert += node_event_heading
                node_alert_text = (
                    f"\nNode Number: {alert_data[entry]['id']}\n"
                    f"Node Status: {alert_data[entry]['node_status']}\n"
                    f"Node S/N: {alert_data[entry]['serial_number']}\n"
                    f"Node Type: {alert_data[entry]['model_number']}\n"
                )
                email_alert += node_alert_text + '\n'
            elif key == 'disk_type':  # drive alert
                email_alert += drive_event_heading
                drive_alert_text = (
                    f"\nNode Number: {alert_data[entry]['node_id']}\n"
                    f"Drive ID: {alert_data[entry]['id']}\n"
                    f"Drive Slot: {alert_data[entry]['slot']}\n"
                    f"Drive Status: {alert_data[entry]['state']}\n"
                    f"Disk Type: {alert_data[entry]['disk_type']}\n"
                    f"Disk Model: {alert_data[entry]['disk_model']}\n"
                    f"Disk S/N: {alert_data[entry]['disk_serial_number']}\n"
                    f"Disk Capacity: {alert_data[entry]['capacity']}\n"
                )
                email_alert += drive_alert_text + '\n'

    email_alert = email_alert.replace('\n', '<br>')
    return email_alert


def send_email(eml: 'EmailMessage') -> None:
    """
    Send email via SMTP.
    """
    mmsg = MIMEText(eml.body, 'html')
    mmsg['Subject'] = eml.subject
    mmsg['From'] = eml.config.sender
    mmsg['To'] = ', '.join(eml.config.mail_to)
    session = smtplib.SMTP(eml.config.server)

    session.sendmail(eml.config.sender, eml.config.mail_to, mmsg.as_string())
    session.quit()


def generate_event_alert_email(config_data: 'ConfigData', email_alert: str) -> None:
    """
    Build and send event alert email.
    """
    subject = f'Event alert for Qumulo cluster: {config_data.cluster_name}'
    body = email_alert
    eml = EmailMessage(config_data, subject, body)

    print('ALERT!! Unhealthy device event(s) found!')

    try:
        send_email(eml)
        print('EMAIL SENT.')
    except Exception as err:
        sys.exit(f'ERROR: {err}\nCheck connection to SMTP server. Exiting...')


def generate_cluster_timeout_email(error: str, config_data: 'ConfigData') -> None:
    """
    Build and send cluster connection timeout alert email.
    """
    subject = f'Script failure for Qumulo cluster: {config_data.cluster_name}'
    body = (
        'The cluster_device_monitor.py script has encountered a '
        'connection timeout and the script has stopped running.<br>'
        "Please check the machine's connection to the cluster over "
        'the required port (default 8000).<br>'
        f'config_data.json - cluster IP: {config_data.cluster_address}<br>'
        f'config_data.json - rest port: {config_data.rest_port}<br>'
        f'<br><b>Error details:</b><br>{error}'
    )
    eml = EmailMessage(config_data, subject, body)

    print('ALERT!! Connection to cluster timed out!')

    try:
        send_email(eml)
        sys.exit(f'EMAIL SENT.\nERROR: {error}. Exiting...')
    except Exception as err:
        sys.exit(
            f'ERROR: {err}\nUnable to send email. Check connection to SMTP server. Exiting...'
        )


#  __  __    _    ___ _   _
# |  \/  |  / \  |_ _| \ | |
# | |\/| | / _ \  | ||  \| |
# | |  | |/ ___ \ | || |\  |
# |_|  |_/_/   \_\___|_| \_|


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """
    Parse arguments if passed into run script command.
    """
    parser = argparse.ArgumentParser(
        description=(
            'This script will check the health of nodes and drives, alerting'
            'when an unhealthy condition is met. The unhealthy conditions are'
            'dead or unhealthy drives and offline nodes.'
        )
    )

    parser.add_argument(
        '--config', '-c', default='config.json', help='Path to the configuration file.'
    )

    parser.add_argument(
        '--print-config-data',
        action='store_true',
        help='Print the parsed representation of the config data.',
    )

    return parser.parse_args(argv)


def main(opts: argparse.Namespace) -> int:
    config_data = load_and_parse_config(opts.config)
    healthy = True
    previous_file = 'cluster_status_previous.json'

    if opts.print_config_data:
        print(config_data)
        return 0

    check_cluster_connectivity(config_data)

    # CHECK AND RECORD CLUSTER STATUS
    rest_client = cluster_login(config_data)
    assert rest_client is not None
    status_of_nodes = retrieve_status_of_cluster_devices(
        rest_client, config_data, 'nodes'
    )
    status_of_drives = retrieve_status_of_cluster_devices(
        rest_client, config_data, 'drives'
    )
    status_of_nodes['drives'] = status_of_drives['drives']
    cluster_status = status_of_nodes
    preserve_cluster_status(cluster_status)
    alert_data, healthy = check_for_unhealthy_objects(cluster_status)

    # PREVIOUS_STATUS LOGIC
    if os.path.exists(previous_file):
        previous_status = load_json(previous_file)
        changed = cluster_status != previous_status
        if not changed:
            healthy = True

    # UNHEALTHY DEVICE ALERTING
    if not healthy:
        email_alert = populate_alert_email_body(alert_data, rest_client, config_data)
        generate_event_alert_email(config_data, email_alert)
        print('Script will restart if on cronjob schedule...')

    delete_previous_cluster_status()
    return 0


if __name__ == '__main__':
    sys.exit(main(parse_args(sys.argv[1:])))
