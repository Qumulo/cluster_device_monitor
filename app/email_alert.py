#!/usr/bin/env python3

"""
When called, email_alert.py will generate an email and send it to all addresses
listed in the config.py file.
"""

from app.config import email_recipients

# TODO: import & configure email module
# TODO: populate values to plug into email

def generate_email():
    """
    Generate email alert and return as string
    """

    # Information for values in alert
    cluster_name = ''
    node_serial = ''
    cluster_uuid = ''
    node_uuid = ''
    node_type = ''
    node_inventory = ''   # XXX: Get rid of this value? 

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