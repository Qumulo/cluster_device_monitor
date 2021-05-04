#!/usr/bin/env python3

"""
The cluster_state_tracking.py script will serve the purpose of recording and 
keeping track of the cluster state related to the health of nodes/drives. The 
script will first need to check for a cluster state file, and create one if it 
doesn't already exist. If it does exist, then the script will compare the
previous and current state of nodes & drives. 
"""

import json
import os
from poll_cluster import (
    retrieve_cluster_nodes_status, 
    retrieve_cluster_drives_status
)

# constants
PREVIOUS_EXISTED = False

# TODO: 

def cluster_state_file_handling():
    """
    If cluster_state.json exists, rename it to cluster_state_previous.json.
    Then create cluster_state.json and write node + drive statuses to file.
    """
    if 'cluster_state.json' in os.listdir():
        os.rename('cluster_state.json','cluster_state_previous.json')
        PREVIOUS_EXISTED = True
    
    with open('cluster_state.json', 'rw') as f:
        f.write(retrieve_cluster_nodes_status)
        f.write(retrieve_cluster_drives_status)

    return PREVIOUS_EXISTED

def compare_states():
    """
    If a previous state file existed, then compare new cluster state to previous
    cluster state and check for any changes, IE nodes offline or drive issues.
    Once the comparison is complete, remove the previous state file.
    """
    pass
