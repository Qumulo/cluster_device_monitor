#!/usr/bin/env python3

"""
The purpose of this script is to log into the cluster and query the cluster's 
status via Python3 API calls. This script will look for nodes that are offline,
drives that have failed and nodes that are out of quorum. The script will get &
retrieve the current state of the cluster and compare the state to the last
known state. If the state has changed and an alert is warranted, the script
will then make a call to the email_alert.py script to send out an email alert
to the specified recipients in config.
"""

from config import API_HOSTNAME, API_USERNAME, API_PASSWORD
import qumulo
import os
import time
from qumulo.rest_client import RestClient

# TODO: add error/exception handling to all functions

def cluster_login(api_hostname, api_username, api_password):
    """
    Log into cluster via info in config.py and return rest client object.
    """
    rest_client = RestClient(api_hostname, 8000)
    rest_client.login(api_username, api_password)

    return rest_client

def retrieve_status_cluster_nodes(rest_client):
    """
    Accept rest_client object to query cluster via API calls. Retrieve status
    and info about nodes, then parse through info and only record relevant 
    fields and return list object.
    """
    node_relevant_fields = [
        'id',
        'node_status',
        'node_name',
        'uuid',
        'model_number',
        'serial_number',
    ]

    status_of_nodes = []
    for num in range(len(rest_client.cluster.list_nodes())):
        modified_dict = {}
        for k,v in rest_client.cluster.list_nodes()[num].items():
            if k in node_relevant_fields:
                modified_dict[k] = v
        status_of_nodes.append(modified_dict)

    return status_of_nodes
    
def retrieve_status_cluster_drives(rest_client):
    """
    Accept rest_client object to query cluster via API calls. Retrieve status
    and info about drives, then parse through info and only record relevant 
    fields and return list object.
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

    status_of_drives = []
    for num in range(len(rest_client.cluster.get_cluster_slots_status())):
        modified_dict = {}
        for k,v in rest_client.cluster.get_cluster_slots_status()[num].items():
            if k in drive_relevant_fields:
                modified_dict[k] = v
        status_of_drives.append(modified_dict)

    return status_of_drives


# testing ....
# rest_client = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)


