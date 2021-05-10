#!/usr/bin/env python3

"""
The cluster_state_tracking.py script will serve the purpose of recording and 
keeping track of the cluster state related to the health of nodes/drives. The 
script will first need to check for a cluster state file, and create one if it 
doesn't already exist. If it does exist, then the script will compare the
previous and current state of nodes & drives. 
"""

# TODO: Add error/exception handling to all functions
# TODO: Figure out how to write node + drive info to json file
# TODO: Fix docstrings
# TODO: fix config file to be json format?

import json
import os
from poll_cluster import (
    retrieve_status_of_cluster_nodes,
    retrieve_status_of_cluster_drives
)

# constants
PREVIOUS_EXISTED = False


def cluster_state_file_handling(status_of_nodes, status_of_drives):
    """
    If cluster_state.json exists, rename it to cluster_state_previous.json.
    Regardless of this, then create cluster_state.json and write node + drive
    statuses to file.
    """
    if 'cluster_state.json' in os.listdir():
        os.rename('cluster_state.json','cluster_state_previous.json')
        PREVIOUS_EXISTED = True
    
    with open('cluster_state.json', 'w') as f:
        json.dump(status_of_nodes, f, indent=4)
        f.write('\n')
        json.dump(status_of_drives, f, indent=4)

    return PREVIOUS_EXISTED

def compare_states():
    """
    If a previous state file existed, then compare new cluster state to previous
    cluster state and check for any changes, IE nodes offline or drive issues.
    Once the comparison is complete, remove the previous state file.
    """
    
    pass

    # if PREVIOUS_EXISTED:



# TESTING  XXX: LATER REMOVE
# status_of_nodes = retrieve_status_cluster_nodes(rest_client)
# status_of_drives = retrieve_status_cluster_drives(rest_client)
# cluster_state_file_handling()