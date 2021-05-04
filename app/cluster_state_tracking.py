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

# TODO: 

# XXX: maybe delete this? 
def check_for_previous_state_file():
    """
    Check for the existence of a cluster state file.
    """
    pass

def create_cluster_state_file():
    """
    Check whether previous cluster state exists and create it if it does not.
    """
    # call functions from poll cluster for node + drive state?
    pass

def compare_states():
    """
    If a previous state file existed, then compare new cluster state to previous
    cluster state and check for any changes, IE nodes offline or drive issues. 
    """
    pass
