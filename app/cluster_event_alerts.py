#!/usr/bin/env python3

"""
poll_cluster.py will log into the cluster via the API, and then issue API calls
to get the status of drives and nodes. The script will parse through the output
and record only the relevant fields that we care about. 
"""

# TODO: add error/exception handling to functions if needed
# TODO: fix docstring for script
# TODO: add timeout logic to cluster_login()

from config import API_HOSTNAME, API_USERNAME, API_PASSWORD
import qumulo
import json
import os
import time
from qumulo.rest_client import RestClient

#   ___                           _    ____ ___ 
#  / _ \ _   _  ___ _ __ _   _   / \  |  _ \_ _|
# | | | | | | |/ _ \ '__| | | | / _ \ | |_) | | 
# | |_| | |_| |  __/ |  | |_| |/ ___ \|  __/| | 
#  \__\_\\__,_|\___|_|   \__, /_/   \_\_|  |___|
#                        |___/                  

def cluster_login(api_hostname, api_username, api_password):
    """
    Log into cluster via info in config.py and return rest client object.
    """
    rest_client = RestClient(api_hostname, 8000)
    rest_client.login(api_username, api_password)

    return rest_client

def get_qq_version(rest_client):
    """
    Query API for Qumulo Core version.
    """

    qq_version = rest_client.version.version()
    print(f'QQ Version: {qq_version}')  # XXX Remove this after testing

    return qq_version    

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
    for num in range(len(rest_client.cluster.list_nodes())):
        new_dict = {}
        for k,v in rest_client.cluster.list_nodes()[num].items():
            if k in node_relevant_fields:
                new_dict[k] = v
        temp_list.append(new_dict)
    
    status_of_nodes = {}
    status_of_nodes['nodes'] = temp_list

    return status_of_nodes

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
    for num in range(len(rest_client.cluster.get_cluster_slots_status())):
        new_dict = {}
        for k,v in rest_client.cluster.get_cluster_slots_status()[num].items():
            if k in drive_relevant_fields:
                new_dict[k] = v
        temp_list.append(new_dict)

    status_of_drives = {}
    status_of_drives['drives'] = temp_list

    return status_of_drives

def combine_statuses_formatting(status_of_nodes, status_of_drives):
    """
    In order to adhere to proper json formatting, this func will combine the
    two status_of_nodes and status_of_drives dictionary objects into one
    single dictionary object.
    """
    status_of_nodes['drives'] = status_of_drives['drives']    
    cluster_status = status_of_nodes
    
    return cluster_status

#   ____                                     ____  _        _            
#  / ___|___  _ __ ___  _ __   __ _ _ __ ___/ ___|| |_ __ _| |_ ___  ___ 
# | |   / _ \| '_ ` _ \| '_ \ / _` | '__/ _ \___ \| __/ _` | __/ _ \/ __|
# | |__| (_) | | | | | | |_) | (_| | | |  __/___) | || (_| | ||  __/\__ \
#  \____\___/|_| |_| |_| .__/ \__,_|_|  \___|____/ \__\__,_|\__\___||___/
#                      |_|                                               

def check_for_previous_state(cluster_status):
    """
    If cluster_state.json exists, rename it to cluster_state_previous.json.
    Regardless of this, also create cluster_state.json and write node + drive
    statuses to file. Return variable for previous_existed.
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
    whether or not the data has changed. Once the comparison is complete, 
    remove the previous state file and rename cluster_state.json to
    cluster_state_previous.json. Return bool for whether there changes.
    """
    
    changes = False

    file1 = 'cluster_state.json'
    file2 = 'cluster_state_previous.json'

    with open(file1) as f1, open(file2) as f2:
        data1, data2 = json.load(f1), json.load(f2)
        changes = data1 == data2

    if changes:
        print('Changes found!!')
        changes = True
        check_for_unhealthy_objects()
    else:
        print('Changes not found!')        

    return changes

def check_for_unhealthy_objects():
    """ 
    Scan the cluster_state.json file to determine whether or not there are 
    unhealthy objects.
    """
    healthy = True

    with open('cluster_state_TEST.json') as f:
        data = json.load(f)
        alert_data = {}
        counter = 1
        
        # scan through json for offline nodes
        for dictobj in data['nodes']:
            for k,v in dictobj.items():
                if k == 'node_status':
                    if v != 'online':
                        print('ALERT!! UNHEALTHY NODE FOUND.')
                        alert_data[f'Event {counter}'] = dictobj
                        counter += 1
                        healthy = False
        # scan through json for unhealthy drives                
        for dictobj in data['drives']:
            for k,v in dictobj.items():
                if k == 'state':
                    if v != 'healthy':
                        print('ALERT!! UNHEALTHY DRIVE FOUND.')                    
                        alert_data[f'Event {counter}'] = dictobj   
                        counter += 1
                        healthy = False
            
    if healthy:
        print('No unhealthy changes found.')

    return alert_data, healthy

#  _____                 _ _ _   _                 _ _ _             
# | ____|_ __ ___   __ _(_) | | | | __ _ _ __   __| | (_)_ __   __ _ 
# |  _| | '_ ` _ \ / _` | | | |_| |/ _` | '_ \ / _` | | | '_ \ / _` |
# | |___| | | | | | (_| | | |  _  | (_| | | | | (_| | | | | | | (_| |
# |_____|_| |_| |_|\__,_|_|_|_| |_|\__,_|_| |_|\__,_|_|_|_| |_|\__, |
#                                                              |___/ 

def generate_alert_email(alert_data):
    """
    Generate email alert and return as string
    """

    string_for_alert = """ ALERT! Unhealthy objectrs found. See below for
    information and engage Qumulo Support in your preferred fashion.
    """

    email_alert = """
    ALERT HERE. (Node: <FILL ME OUT>)
    Cluster Name:  <FILL ME OUT>
    Serial Number	<FILL ME OUT>
    Cluster UUID	<FILL ME OUT>
    Node UUID	<FILL ME OUT>
    Node Type	<FILL ME OUT>
    Node Inventory	<FILL ME OUT>
    Software Version	<FILL ME OUT>
    """

    return email_alert

def send_email(email_alert, email_recipients):
    """
    Send an email populated with alert information to all email addresses in
    receipients list specified in config.py.
    """

    pass

#  __  __       _       
# |  \/  | __ _(_)_ __  
# | |\/| |/ _` | | '_ \ 
# | |  | | (_| | | | | |
# |_|  |_|\__,_|_|_| |_|
                      

def main():
    rest_client = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)
    qq_version = get_qq_version(rest_client)
    status_of_nodes = retrieve_status_of_cluster_nodes(rest_client)
    status_of_drives = retrieve_status_of_cluster_drives(rest_client)
    cluster_status = combine_statuses_formatting(status_of_nodes, status_of_drives)
    previous_existed = check_for_previous_state(cluster_status)
    # if previous_existed:
    #     compare_states()
    # else:
    #     alert_data, healthy = check_for_unhealthy_objects()


if __name__ == '__main__':
    main()
