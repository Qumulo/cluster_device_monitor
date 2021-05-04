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

from config import API_HOSTNAME,API_USERNAME,API_PASSWORD
import qumulo
import os
import time
from qumulo.rest_client import RestClient

def cluster_login(api_hostname, api_username, api_password):
    """
    Log into cluster via info in config.py and return rest client object.
    """
    print('Logging into cluster...')
    rc = RestClient(api_hostname, 8000)
    rc.login(api_username, api_password)

    return rc

def retrieve_cluster_nodes_status():
    """
    Retrieve status and information about nodes.
    """
    rc.cluster.list_nodes()
    

def retrieve_cluster_drives_status():
    """
    Retrieve status and information about drives.
    """
    rc.cluster.get_cluster_slots_status()





# testing ....
# rc = cluster_login(API_HOSTNAME, API_USERNAME, API_PASSWORD)




"""
Notes for later:
- Get the value of a first node status: rc.cluster.list_nodes()[0]['node_status']
"""