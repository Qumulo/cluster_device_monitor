#!/usr/bin/env python3

"""
poll_cluster.py will log into the cluster via the API, and then issue API calls
to get the status of drives and nodes. The script will parse through the output
and record only the relevant fields that we care about. 
"""

# TODO: fix docstrings for all functions
# TODO: adding typing to function defs

# XXX Unused
# import argparse
# import time
# from datetime import datetime
# from smtplib import SMTPRecipientsRefused, SMTPConnectError

import json
import os
import smtplib
import socket
import sys
from email.mime.text import MIMEText
import qumulo
from qumulo.rest_client import RestClient
from qumulo.lib.request import RequestError

#  _   _ _____ _     ____  _____ ____  ____
# | | | | ____| |   |  _ \| ____|  _ \/ ___|
# | |_| |  _| | |   | |_) |  _| | |_) \___ \
# |  _  | |___| |___|  __/| |___|  _ < ___) |
# |_| |_|_____|_____|_|   |_____|_| \_\____/

def load_json(file: str):
    """
    Load a file and ensure that it's valid JSON.
    """
    try:
        file_fh = open(file, 'r')
        data = json.load(file_fh)
        return data
    except ValueError as error:
        sys.exit(f'Invalid JSON file: {file}. Error: {error}')
    finally:
        file_fh.close()

def check_cluster_connectivity_with_socket(config_file):
    host_ip = config_file['cluster_settings']['cluster_address']
    rest_port = config_file['cluster_settings']['rest_port']

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    result_of_check = sock.connect((host_ip, rest_port))

    if result_of_check != 0:
        print('ERROR! Unable to communicate with cluster over specified port.')
        sys.exit(f'Err code: {result_of_check}\nPlease try again. Exiting...')

def load_config(config_file: str):
    """
    Load json as json dictionary-like object for parsing.
    """    
    if os.path.exists(config_file):
        return load_json(config_file)
    else:
        sys.exit(f'Config file "{config_file}" does not exist. Exiting...')

def delete_previous_cluster_state_file():
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

def cluster_login(api_hostname, api_username, api_password):
    """
    Accept api_hostname, api_username and api_password as parameters. Log into
    cluster via Qumulo Rest API. Return rest_client for all future API calls.
    """
    
    try:
        rest_client = RestClient(api_hostname, 8000)
        rest_client.login(api_username, api_password)
        return rest_client
    except OSError as e:
        sys.exit(f'{e}\nExiting...')
    except TimeoutError as e:
        sys.exit(f'{e}\nExiting...')
    except RequestError as e:
        print('Invalid credentials. Please check config file & try again.')
        sys.exit('Exiting...')

def get_cluster_name(rest_client):
    """
    Query API for cluster name. Return cluster name as string.
    """
    try:
        cluster_name = rest_client.cluster.get_cluster_conf()['cluster_name']
        return cluster_name
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def get_qq_version(rest_client):
    """
    Query API for Qumulo Core version. Return version as string.
    """
    try:
        qq_version = rest_client.version.version()['revision_id']
        return qq_version
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def get_cluster_time(rest_client):
    """
    Get current cluster time and return as cluster_time.
    """
    try:
        cluster_time = rest_client.time_config.get_time_status()['time']
        return cluster_time
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def get_cluser_uuid(rest_client):
    """
    Query API for cluster UUID number. Return UUID as string.
    """
    try:
        cluster_uuid = rest_client.node_state.get_node_state()['cluster_id']
        return cluster_uuid
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def retrieve_status_of_cluster_nodes(rest_client):
    """
    Accept rest_client object to query via API call to retrieve info/status for
    nodes. Parse through information and record relevant information. Return
    dict object to later dump as json.
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
    status_of_nodes = {}

    try:
        for num in range(len(rest_client.cluster.list_nodes())):
            new_dict = {}
            for k,v in rest_client.cluster.list_nodes()[num].items():
                if k in node_relevant_fields:
                    new_dict[k] = v
            temp_list.append(new_dict)
        
        status_of_nodes['nodes'] = temp_list
        return status_of_nodes
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def retrieve_status_of_cluster_drives(rest_client):
    """
    Accept rest_client object to query via API call to retrieve info/status for
    drives. Parse through information and record relevant information. Return
    dict object to later dump as json.
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
    status_of_drives = {}

    try:
        for num in range(len(rest_client.cluster.get_cluster_slots_status())):
            new_dict = {}
            for k,v in rest_client.cluster.get_cluster_slots_status()[num].items():
                if k in drive_relevant_fields:
                    new_dict[k] = v
            temp_list.append(new_dict)

        status_of_drives['drives'] = temp_list
        return status_of_drives
    except TimeoutError as e:
        api_timeout_send_email()
        sys.exit(f'{e}\nExiting...')

def combine_statuses_formatting(status_of_nodes, status_of_drives):
    """
    In order to adhere to proper json formatting, this func will combine the
    two status_of_nodes and status_of_drives dictionary objects into one
    single dictionary object and return this as cluster_status.
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

def check_for_previous_state(cluster_status):
    """
    If cluster_state.json exists, rename it to cluster_state_previous.json.
    Regardless of this, also create cluster_state.json and write node + drive
    statuses to file. Return boolean for previous_existed.
    """
    if 'cluster_state.json' in os.listdir():
        os.rename('cluster_state.json','cluster_state_previous.json')
        previous_existed = True
    else:
        previous_existed = False

    with open('cluster_state.json', 'w') as f:
        json.dump(cluster_status, f, indent=4)

    return previous_existed

def compare_states():
    """
    Only being ran if previous_existed is true, this func will compare the
    json files for the previous and current cluster state. Return bool for
    whether or not the data has changed. Return bool for if changes were found.
    """    

    file1 = 'cluster_state.json'
    file2 = 'cluster_state_previous.json'

    with open(file1) as f1, open(file2) as f2:
        data1, data2 = json.load(f1), json.load(f2)
        changes = data1 != data2

    # XXX: testing
    if changes:
        print('Changes found!! Scanning for unhealthy objects.')
    else:
        print('Changes not found! NOT scanning for unhealthy objects')

    return changes

def get_current_state():
    data = {}

    with open('cluster_state.json') as f:
        data = json.load(f)

    return data

def check_for_unhealthy_objects():
    """
    Scan the cluster_state.json file to determine whether or not there are
    unhealthy objects. If there are unhealthy objects, append the data to
    new dict object called alert_data, which will later be used to populate
    the alert. Also return whether or not cluster is healthy as bool.
    """
    healthy = True

    data = get_current_state()
    nodes = data['nodes']

    alert_data = {}
    counter = 1

    # scan through json for offline nodes
    for node in nodes:
        if 'online' not in node['node_status']:
            print('ALERT!! UNHEALTHY NODE FOUND.')  # XXX: Later remove
            alert_data[f'Event {counter}'] = node
            counter += 1
            healthy = False
    # scan through json for unhealthy drives
    for dictobj in data['drives']:
        for k, v in dictobj.items():
            if k == 'state':
                if v != 'healthy':
                    print('ALERT!! UNHEALTHY DRIVE FOUND.')  # XXX: Later remove
                    alert_data[f'Event {counter}'] = dictobj
                    counter += 1
                    healthy = False

    if healthy:
        print('No unhealthy changes found.')

    return alert_data, healthy

# XXX: old - remove after testing
def check_for_unhealthy_objects():
    """ 
    Scan the cluster_state.json file to determine whether or not there are 
    unhealthy objects. If there are unhealthy objects, append the data to
    new dict object called alert_data, which will later be used to populate
    the alert. Also return whether or not cluster is healthy as bool. 
    """
    healthy = True
    alert_data = {}
    counter = 1

    with open('cluster_state.json') as f:
        data = json.load(f)
        
    # scan through json file for offline nodes
    for dictobj in data['nodes']:
        for k,v in dictobj.items():
            if k == 'node_status':
                if v != 'online':
                    print('ALERT!! UNHEALTHY NODE FOUND.') # XXX: Later remove
                    alert_data[f'Event {counter}'] = dictobj
                    counter += 1
                    healthy = False
    # scan through json file for unhealthy drives
    for dictobj in data['drives']:
        for k,v in dictobj.items():
            if k == 'state':
                if v != 'healthy':
                    print('ALERT!! UNHEALTHY DRIVE FOUND.') # XXX: Later remove 
                    alert_data[f'Event {counter}'] = dictobj
                    counter += 1
                    healthy = False
            
    if healthy:
        print('No unhealthy changes found.')
    return alert_data, healthy

#  _____ __  __    _    ___ _     ___ _   _  ____
# | ____|  \/  |  / \  |_ _| |   |_ _| \ | |/ ___|
# |  _| | |\/| | / _ \  | || |    | ||  \| | |  _
# | |___| |  | |/ ___ \ | || |___ | || |\  | |_| |
# |_____|_|  |_/_/   \_\___|_____|___|_| \_|\____|
                                                
def generate_alert_email(alert_data, rest_client):
    """
    Generate email alert and return as string
    """
    qq_version = get_qq_version(rest_client)
    cluster_name = get_cluster_name(rest_client)
    cluster_uuid = get_cluser_uuid(rest_client)
    cluster_time = get_cluster_time(rest_client)
    counter = 0
    alert_header = '=' * 19 + ' CLUSTER EVENT ALERT! ' + '=' * 19
    node_event_heading = '=' * 23 + ' NODE OFFLINE ' + '=' * 23
    drive_event_heading = '=' * 21 + ' DRIVE UNHEALTHY ' + '=' * 22

    for objs in alert_data:
        counter += 1
    email_alert = f"""{alert_header}\nUnhealthy object(s) found. See below for\
 info and engage Qumulo Support in your preferred fashion.\n
Cluster name: {cluster_name}
Cluster UUID: {cluster_uuid}
Approx. time: {cluster_time} UTC\n
{counter} Event(s) found:\n"""

    for item in alert_data:
        for k,v in alert_data[item].items():
            if k == 'node_status':    # this is a node alert
                email_alert += node_event_heading
                node_alert_text = f"""
Node number: {alert_data[item]['id']}
Node status: {alert_data[item]['node_status']}
Serial Number: {alert_data[item]['serial_number']}
Node UUID: {alert_data[item]['uuid']}           
Node Type: {alert_data[item]['model_number']}
Qumulo Core Version: {qq_version}"""
                email_alert += node_alert_text + '\n\n'

            elif k == 'disk_type':    # this is a drive alert
                email_alert += drive_event_heading
                drive_alert_text = f"""
Node number: {alert_data[item]['node_id']}
Drive slot: {alert_data[item]['slot']}
Drive status: {alert_data[item]['state']}
Slot type: {alert_data[item]['slot_type']}
Disk type: {alert_data[item]['disk_type']}
Disk model: {alert_data[item]['disk_model']}
Disk serial number: {alert_data[item]['disk_serial_number']}
Disk capacity: {alert_data[item]['capacity']}"""
                email_alert += drive_alert_text + '\n'
    
    email_alert = email_alert.replace('\n', '<br>')
    return email_alert

def get_email_settings(config_file):
    """
    Pull various email settings from config file.
    """
    email_recipients = []
    sender_addr = config_file['email_settings']['sender_address']
    server_addr = config_file['email_settings']['server_address']

    for email_addr in config_file['email_settings']['mail_to']:
        email_recipients.append(email_addr)

    return sender_addr, server_addr, email_recipients

def alert_send_email(config_file, email_alert):
    """
    Send an email populated with alert information to all email addresses in
    receipients list specified in config.py.
    """
    sender_addr, server_addr, email_recipients = get_email_settings(config_file)
    clustername = config_file['cluster_settings']['cluster_name']
    subject = f'Event alert for Qumulo cluster: {clustername}'

    # Compose the email to be sent based off received data.
    mmsg = MIMEText(email_alert, 'html')
    mmsg['Subject'] = subject
    mmsg['From'] = sender_addr
    mmsg['To'] = ', '.join(email_recipients)

    session = smtplib.SMTP(server_addr)
    session.sendmail(sender_addr, email_recipients, mmsg.as_string())
    session.quit()

def api_timeout_send_email():
    """
    In the event of API calls failing due to timeout/disconnect, an alert
    should be sent to notify the admin(s) of the failure.
    """
    sender_addr, server_addr, email_recipients = get_email_settings(config_file)
    clustername = config_file['cluster_settings']['cluster_name']
    subject = f'Script failure for Qumulo cluster: {clustername}'
    email_body = """The cluster_event_alerts.py script has encountered an \
API connection timeout and the script has stopped running. Please check the \
machine's connection to the cluster over the required port (default 8000)."""

    mmsg = MIMEText(email_body, 'html')
    mmsg['Subject'] = subject
    mmsg['From'] = sender_addr 
    mmsg['To'] = ', '.join(email_recipients)

    session = smtplib.SMTP(server_addr)
    session.sendmail(sender_addr, email_recipients, mmsg.as_string())
    session.quit()

#  __  __    _    ___ _   _
# |  \/  |  / \  |_ _| \ | |
# | |\/| | / _ \  | ||  \| |
# | |  | |/ ___ \ | || |\  |
# |_|  |_/_/   \_\___|_| \_|

def main():
    # load config, check connectivity, query API & gather data
    config_file = load_config('config.json')
    # check_cluster_connectivity_with_socket(config_file)
    API_HOSTNAME = config_file['cluster_settings']['cluster_address']
    API_USERNAME = config_file['cluster_settings']['username']
    API_PASSWORD = config_file['cluster_settings']['password']
    rest_client = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)
    status_of_nodes = retrieve_status_of_cluster_nodes(rest_client)
    status_of_drives = retrieve_status_of_cluster_drives(rest_client)
    cluster_status = combine_statuses_formatting(status_of_nodes, status_of_drives)
    previous_existed = check_for_previous_state(cluster_status)

    # previous state logic handling
    if previous_existed:
        changes = compare_states()
        if changes:
            alert_data, healthy = check_for_unhealthy_objects()
        else:
            healthy = True
    else:
        alert_data, healthy = check_for_unhealthy_objects()

    # email alert generation
    if not healthy:
        print('Cluster event found! Generating & sending email')
        email_alert = generate_alert_email(alert_data, rest_client)
        alert_send_email(config_file, email_alert)
    else:
        print('New unhealthy objects were NOT found. Closing script') # XXX: Remove l8r
    
    delete_previous_cluster_state_file()
    return 0

if __name__ == '__main__':
    sys.exit(main())