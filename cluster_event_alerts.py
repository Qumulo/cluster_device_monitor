#!/usr/bin/env python3

"""
cluster_event_alerts.py interacts with the Qumulo Rest API to retrieve the
status of NODES and DRIVES. The cluster response data is recorded into
cluster_state.json, which is used to parse through for unhealthy nodes and
drives. If unhealthy objects are found, an email will be sent to all addresses
defined in the config.json file.

cluster_event_alerts.py has logic to look for previous iterations of the script
being ran and will not send email alerts if the alerts were previously
generated & sent. The script also contains logic to send an email alert if it
loses connection with the API.
"""

# TODO: LINTING
# TODO: attention to all XXX tags

# TESTING
# XXX: Test API timeout functionality
# XXX: Verify API timeout email formatting looks correct
# XXX: CHECK FORMATTING WITH:
#       - ONLY ONE NODE DOWN
#       - ONLY ONE DRIVE DOWN
#       - TWO+ NODES DOWN
#       - TWO+ DRIVES DOWN


# Import Python Libraries
from time import sleep
import json
import os
import smtplib
import socket
import sys
from collections import namedtuple
from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Any, Dict, Tuple

# import Qumulo REST libraries:
from qumulo.rest_client import RestClient
from qumulo.lib.request import RequestError

#   ____ _     ___  ____    _    _     ____
#  / ___| |   / _ \| __ )  / \  | |   / ___|
# | |  _| |  | | | |  _ \ / _ \ | |   \___ \
# | |_| | |__| |_| | |_) / ___ \| |___ ___) |
#  \____|_____\___/|____/_/   \_\_____|____/

RestInfo = namedtuple('RestInfo', ['conninfo', 'creds'])


#   ____ _        _    ____ ____  _____ ____
#  / ___| |      / \  / ___/ ___|| ____/ ___|
# | |   | |     / _ \ \___ \___ \|  _| \___ \
# | |___| |___ / ___ \ ___) |__) | |___ ___) |
#  \____|_____/_/   \_\____/____/|_____|____/


@dataclass
class EmailMessage:
    """Construct email"""
    cluster_name = ''
    subject = None
    body = None
    email_recipients = []
    sender = ''
    server = ''


#  _   _ _____ _     ____  _____ ____  ____
# | | | | ____| |   |  _ \| ____|  _ \/ ___|
# | |_| |  _| | |   | |_) |  _| | |_) \___ \
# |  _  | |___| |___|  __/| |___|  _ < ___) |
# |_| |_|_____|_____|_|   |_____|_| \_\____/


def load_json(config_file: str) -> Dict[str, Any]:
    """
    Load a file as JSON.
    """
    try:
        with open(config_file, 'r') as fh:
            return json.load(fh)
    except ValueError as e:
        sys.exit(f'Invalid JSON file: {config_file}. ERROR: {e}')
    finally:
        fh.close()


def check_cluster_connectivity_with_socket(config_file: str) -> None:
    """
    Use socket to verify communication with cluster IP.
    """
    try:
        host_ip = config_file['cluster_settings']['cluster_address']
        rest_port = config_file['cluster_settings']['rest_port']
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host_ip, int(rest_port)))
        sock.shutdown(socket.SHUT_WR)
        sock.close()
    except ConnectionRefusedError as e:
        sys.exit(f'ERROR: {e}\nCheck port connectivity & try again. Exiting...')
    except socket.timeout as e:
        sys.exit(f'ERROR: {e}\nCheck connection & try again. Exiting...')


def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load json file object for parsing.
    """
    if os.path.exists(config_file):
        return load_json(config_file)
    else:
        sys.exit(f'Config file "{config_file}" does not exist. Exiting...')


def delete_previous_cluster_state_file() -> None:
    """
    Delete cluster_state_previous.json if it exists.
    """
    if 'cluster_state_previous.json' in os.listdir():
        os.remove('cluster_state_previous.json')


#   ___  _   _ _____ ______   __     _    ____ ___
#  / _ \| | | | ____|  _ \ \ / /    / \  |  _ \_ _|
# | | | | | | |  _| | |_) \ V /    / _ \ | |_) | |
# | |_| | |_| | |___|  _ < | |    / ___ \|  __/| |
#  \__\_\\___/|_____|_| \_\|_|___/_/   \_\_|  |___|
#                           |_____|


def cluster_login(config_file) -> RestInfo:
    """
    Log into cluster via Qumulo Rest API.
    """
    api_hostname = config_file['cluster_settings']['cluster_address']
    api_username = config_file['cluster_settings']['username']
    api_password = config_file['cluster_settings']['password']

    try:
        rest_client = RestClient(api_hostname, 8000)
        rest_client.login(api_username, api_password)
        return rest_client
    except TimeoutError as e:
        sys.exit(f'{e}\nExiting...')
    except RequestError as e:
        print('ERROR: Invalid credentials. Please check config file & try again.')
        sys.exit('Exiting...')


def get_cluster_name(rest_client: RestInfo) -> str:
    """
    API Query: Cluster name
    """
    try:
        cluster_name = rest_client.cluster.get_cluster_conf()['cluster_name']
        return cluster_name
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')


def get_qq_version(rest_client: RestInfo) -> str:
    """
    API Query: Qumulo Core version
    """
    try:
        qq_version = rest_client.version.version()['revision_id']
        return qq_version
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')


def get_cluster_time(rest_client: RestInfo) -> str:
    """
    API Query: Cluster time
    """
    try:
        cluster_time = rest_client.time_config.get_time_status()['time']
        return cluster_time
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')


def get_cluser_uuid(rest_client: RestInfo) -> str:
    """
    API Query: UUID number
    """
    try:
        cluster_uuid = rest_client.node_state.get_node_state()['cluster_id']
        return cluster_uuid
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')


def retrieve_status_of_cluster_nodes(rest_client: RestInfo) -> Dict[str, Any]:
    """
    API Query: Node statuses // Data parsing
    """
    node_relevant_fields = [
        'id',
        'node_status',
        'node_name',
        'uuid',
        'model_number',
        'serial_number',
    ]
    temp_list = []
    new_dict = {}
    status_of_nodes = {}

    try:
        cluster_nodes = rest_client.cluster.list_nodes()
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')

    for num in range(len(cluster_nodes)):
        for k,v in cluster_nodes[num].items():
            if k in node_relevant_fields:
                new_dict[k] = v
        temp_list.append(new_dict)
    status_of_nodes['nodes'] = temp_list

    return status_of_nodes


def retrieve_status_of_cluster_drives(rest_client: RestInfo) -> Dict[str, Any]:
    """
    API Query: Drive statuses // Data parsing
    """
    drive_relevant_fields = [
        'id',
        'node_id',
        'slot',
        'state',
        'slot_type',
        'disk_type',
        'disk_model',
        'disk_serial_number',
        'capacity',
    ]
    temp_list = []
    new_dict = {}
    status_of_drives = {}

    try:
        cluster_slots = rest_client.cluster.get_cluster_slots_status()
    except TimeoutError as e:
        generate_api_timeout_email(e)
        sys.exit(f'{e}\nExiting...')

    for num in range(len(cluster_slots)):
        for k,v in cluster_slots[num].items():
            if k in drive_relevant_fields:
                new_dict[k] = v
        temp_list.append(new_dict)
    status_of_drives['drives'] = temp_list

    return status_of_drives


def combine_statuses_formatting(
    status_of_nodes: Dict[str, Any],
    status_of_drives: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Combine dictionaries for node & drive status.
    """
    status_of_nodes['drives'] = status_of_drives['drives']
    cluster_status = status_of_nodes

    return cluster_status


#  ____  _______     _____ _______        __       ____    _  _____  _
# |  _ \| ____\ \   / /_ _| ____\ \      / /      |  _ \  / \|_   _|/ \
# | |_) |  _|  \ \ / / | ||  _|  \ \ /\ / /       | | | |/ _ \ | | / _ \
# |  _ <| |___  \ V /  | || |___  \ V  V /        | |_| / ___ \| |/ ___ \
# |_| \_\_____|  \_/  |___|_____|  \_/\_/____ ____|____/_/   \_\_/_/   \_\
#                                      |_____|_____|


def check_for_previous_state(cluster_status: Dict[str, Any]) -> bool:
    """
    Current + previous 'cluster_state.json' file handling.
    """
    if 'cluster_state.json' in os.listdir():
        os.rename('cluster_state.json','cluster_state_previous.json')
        previous_existed = True
        print('PREVIOUS RUN FILE "CLUSTER_STATE.JSON" FOUND')           # XXX TESTING
    else:
        previous_existed = False
    with open('cluster_state.json', 'w') as f:
        json.dump(cluster_status, f, indent=4)

    return previous_existed


def compare_states() -> bool:
    """
    Compare the json files for the previous/current state.
    """

    # file1 = 'cluster_state.json'
    file1 = 'cluster_state_unhealthy_devices_TEST.json'                        # XXX: TESTING
    file2 = 'cluster_state_previous.json'
    # file2 = 'cluster_state_unhealthy_devices_TEST.json'                      # XXX: TESTING

    with open(file1) as f1, open(file2) as f2:
        data1, data2 = json.load(f1), json.load(f2)
        if data1 != data2:                                                     # XXX: TESTING
            print('CHANGES FOUND!! Scanning for unhealthy objects.')           # XXX: TESTING
        else:                                                                  # XXX: TESTING
            print('CHANGES NOT FOUND!! NOT scanning for unhealthy objects')     # XXX: TESTING

        return data1 != data2                                                  # XXX: BUMP UP


def check_for_unhealthy_objects() -> Tuple[dict, bool]:
    """
    Parse through cluster_state.json for unhealthy objects.
    """

    # with open('cluster_state.json') as f:
    with open('cluster_state_unhealthy_devices_TEST.json') as f:                # XXX: TESTING
        data = json.load(f)
    nodes = data['nodes']
    drives = data['drives']
    alert_data = {}
    healthy = True
    counter = 1

    # scan through json for offline nodes
    for node in nodes:
        if node['node_status'] != 'online':
            print('ALERT!! UNHEALTHY NODE(S) FOUND.')
            alert_data[f'Event {counter}'] = node
            counter += 1
            healthy = False
    # scan through json for unhealthy drives
    for drive in drives:
        if drive['state'] != 'healthy':
            print('ALERT!! UNHEALTHY DRIVE(S) FOUND.')
            alert_data[f'Event {counter}'] = drive
            counter += 1
            healthy = False
    if healthy:
        print('No unhealthy changes found.')

    print(f'ALERT DATA:\n\n{alert_data}')
    return alert_data, healthy


#  _____ __  __    _    ___ _     ___ _   _  ____
# | ____|  \/  |  / \  |_ _| |   |_ _| \ | |/ ___|
# |  _| | |\/| | / _ \  | || |    | ||  \| | |  _
# | |___| |  | |/ ___ \ | || |___ | || |\  | |_| |
# |_____|_|  |_/_/   \_\___|_____|___|_| \_|\____|


def generate_alert_email(
        alert_data: Dict[str, Any],
        rest_client: RestInfo
) -> str:
    """
    Generate email body for alert information.
    """
    qq_version = get_qq_version(rest_client)
    cluster_name = get_cluster_name(rest_client)
    cluster_uuid = get_cluser_uuid(rest_client)
    cluster_time = get_cluster_time(rest_client)

    alert_header = '<b>=' * 19 + ' CLUSTER EVENT ALERT! ' + '</b>=' * 19
    node_event_heading = '<b>=' * 23 + ' NODE OFFLINE ' + '</b>=' * 23
    drive_event_heading = '<b>=' * 21 + ' DRIVE UNHEALTHY ' + '</b>=' * 21
    email_alert = (
        f'{alert_header}\nUnhealthy object(s) found. See below for '
        'info and engage Qumulo Support in your preferred fashion.\n'
        f'Cluster name: {cluster_name}\n'
        f'Cluster UUID: {cluster_uuid}\n'
        f'Approx. time: {cluster_time} UTC\n\n'
        f'<i>{len(alert_data)} Event(s) found:</i>\n'
    )

    for item in alert_data:
        # for k,v in alert_data[item].items():                        # XXX: previous; remove?
        for k in alert_data[item].items():
            if k == 'node_status': # node alert
                email_alert += node_event_heading
                node_alert_text = (
                    f"\nNode Number: {alert_data[item]['id']}\n"
                    f"Node Status: {alert_data[item]['node_status']}\n"
                    f"Node S/N: {alert_data[item]['serial_number']}\n"
                    f"Node UUID: {alert_data[item]['uuid']}\n"
                    f"Node Type: {alert_data[item]['model_number']}\n"
                    f"Qumulo Core Version: {qq_version}\n"
                )
                email_alert += node_alert_text + '\n'
            elif k == 'disk_type': # drive alert
                email_alert += drive_event_heading
                drive_alert_text = (
                    f"\nNode Number: {alert_data[item]['node_id']}\n"
                    f"Drive Slot: {alert_data[item]['slot']}\n"
                    f"Drive Status: {alert_data[item]['state']}\n"
                    f"Slot Type: {alert_data[item]['slot_type']}\n"
                    f"Disk Type: {alert_data[item]['disk_type']}\n"
                    f"Disk Model: {alert_data[item]['disk_model']}\n"
                    f"Disk S/N: {alert_data[item]['disk_serial_number']}\n"
                    f"Disk Capacity: {alert_data[item]['capacity']}\n"
                    f"Qumulo Core Version: {qq_version}\n"
                )
                email_alert += drive_alert_text + '\n'

    email_alert = email_alert.replace('\n', '<br>')
    return email_alert


def get_email_settings(config_file: str) -> Tuple[str, str, list]:
    """
    Pull email settings from config file.
    """
    email_recipients = []
    sender = config_file['email_settings']['sender']
    server = config_file['email_settings']['server']

    for email_addr in config_file['email_settings']['mail_to']:
        email_recipients.append(email_addr)

    return sender, server, email_recipients


def send_email(email_message: str) -> None:
    """
    Send email via SMTP.
    """
    e = email_message
    mmsg = MIMEText(e.body, 'html')
    mmsg['Subject'] = e.subject
    mmsg['From'] = e.sender
    mmsg['To'] = ', '.join(e.email_recipients)

    session = smtplib.SMTP(e.server)
    session.sendmail(e.sender, e.email_recipients, mmsg.as_string())
    session.quit()


def generate_event_alert_email(config_file: str, email_alert: str) -> None:
    """
    Build and send event alert email.
    """
    e = EmailMessage()
    e.cluster_name = config_file['cluster_settings']['cluster_name']
    e.subject = f'Event alert for Qumulo cluster: {e.cluster_name}'
    e.body = email_alert
    (
        e.sender, e.server, e.email_recipients
    ) = get_email_settings(config_file)

    send_email(e)


def generate_api_timeout_email(error: str) -> None:
    """
    Build and send API timeout alert email.
    """
    config_file = load_config('config.json')

    e = EmailMessage()
    e.cluster_name = config_file['cluster_settings']['cluster_name']
    e.subject = f'Script failure for Qumulo cluster: {e.cluster_name}'
    (
        e.sender, e.server, e.email_recipients
    ) = get_email_settings(config_file)
    e.body = (
        'The cluster_event_alerts.py script has encountered an '
        'API connection timeout and the script has stopped running.\n'
        'Please check the machine\'s connection to the cluster over '
        'the required port (default 8000).'
        f'\nError message: {error}'
    )

    send_email(e)


#  __  __    _    ___ _   _
# |  \/  |  / \  |_ _| \ | |
# | |\/| | / _ \  | ||  \| |
# | |  | |/ ___ \ | || |\  |
# |_|  |_/_/   \_\___|_| \_|


def main():
    """
    Run script.
    """
    # load config, check connectivity, query API & gather data
    config_file = load_config('config.json')
    check_cluster_connectivity_with_socket(config_file)
    rest_client = cluster_login(config_file)
    status_of_nodes = retrieve_status_of_cluster_nodes(rest_client)
    status_of_drives = retrieve_status_of_cluster_drives(rest_client)
    cluster_status = combine_statuses_formatting(
        status_of_nodes,
        status_of_drives
        )
    previous_existed = check_for_previous_state(cluster_status)
    # previous state logic handling
    if previous_existed:
        changes = compare_states()
        if changes:
            alert_data, healthy = check_for_unhealthy_objects()
        else:
            healthy = True
    else:
        print('Previous did not exist.. checking for unhealthy objects.') # XXX TESTING
        alert_data, healthy = check_for_unhealthy_objects()

    # email alert generation
    if not healthy:
        print(
            'Cluster event found! Generating & sending email'
            '\nScript running...'
            )
        email_alert = generate_alert_email(alert_data, rest_client)
        generate_event_alert_email(config_file, email_alert)
    else:
        print('New unhealthy objects were NOT found. Closing script') # XXX: TESTING

    delete_previous_cluster_state_file()
    sleep(1) # XXX
    return 0


if __name__ == '__main__':
    sys.exit(main())
