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
    status_of_nodes["nodes"] = temp_list

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
    status_of_drives["drives"] = temp_list

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

def cluster_state_file_handling(cluster_status):
    """
    If cluster_state.json exists, rename it to cluster_state_previous.json.
    Regardless of this, then create cluster_state.json and write node + drive
    statuses to file. Return variable for previous_existed.
    """
    if 'cluster_state.json' in os.listdir():
        os.rename('cluster_state.json','cluster_state_previous.json')
        previous_existed = True
    else:
        previous_existed = False
        
    with open('cluster_state.json', 'w') as f:
        json.dump(cluster_status, f, indent=4)
        # f.write('\n')
        # json.dump(status_of_drives, f, indent=4)

    return previous_existed

def compare_states():
    """
    If a previous state file existed, then compare new cluster state to previous
    cluster state and check for any changes, IE nodes offline or drive issues.
    Once the comparison is complete, remove the previous state file and rename
    cluster_state.json to cluster_state_previous.json.
    """
    
    # XXX: Might not need this
    changes = False
    
    # XXX: add logic here to compare the two files and look for CHANGES
    if previous_existed:
        pass  
    else:
        pass
    
    return changes

def check_for_unhealthy_objects():
    pass

def issue_alert():
    pass

# testing ....
rest_client = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)
status_of_nodes = retrieve_status_of_cluster_nodes(rest_client)
status_of_drives = retrieve_status_of_cluster_drives(rest_client)
cluster_status = combine_statuses_formatting(status_of_nodes, status_of_drives)
previous_existed = cluster_state_file_handling(cluster_status)
changes = compare_states()

