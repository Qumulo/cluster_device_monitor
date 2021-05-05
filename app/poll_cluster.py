#!/usr/bin/env python3

"""
poll_cluster.py will log into the cluster via the API, and then issue API calls
to get the status of drives and nodes. The script will parse through the output
and record only the relevant fields that we care about. 
"""

from config import API_HOSTNAME, API_USERNAME, API_PASSWORD
import qumulo
import os
import time
from qumulo.rest_client import RestClient

# TODO: add error/exception handling to all functions
# TODO: fix docstring for script
# TODO: add timeout logic to cluster_login()

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

# testing ....
# rest_client = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)


