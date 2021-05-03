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

# TODO
def cluster_login():
    pass

# TODO
def check_for_known_status():
    pass

# TODO
def query_status():
    pass

