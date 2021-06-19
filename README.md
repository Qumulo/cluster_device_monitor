# Qumulo Cluster Device Monitor

## Table of contents

  * [ChangeLog](#changelog)
  * [Introduction](#introduction)
  * [Installation](#installation)
  * [Requirements](#requirements)
  * [Configuration](#configuration)
  * [Permissions](#permissions)
  * [Examples](#examples)
  * [Notes](#notes)

## ChangeLog

*  06/15/21: V1.0 - Functional and completed, for now!

## Introduction
This script generates email alerts for a Qumulo cluster using the REST API when offline nodes & unhealthy drives are found.

The Qumulo API tools are required to make the script work and and they are available for download from your Qumulo cluster. For more information, please check out the [Qumulo GitHub](https://qumulo.github.io/) page for more information on the API.

The script contains logic to look for a previously ran iteration and NOT generate email alerts if the necessary alerts were already generated. If unhealthy changes arise the script will detect this and generate a new email alert.

If any of the alert conditions are triggered, a single email will be sent to all of the configured recipients.

The suggested method to run this script is via a `cron` job which periodically executes the script. For more information regarding `cron` please check out [Ubuntu's Cron How To](https://help.ubuntu.com/community/CronHowto).

Lastly, all email alerts include a time stamp indicating when the alert was sent.


## Requirements

The script has the following requirements:

  * A Linux machine, preferably Ubuntu 16.04 or newer.
  * Python 3.6 or newer. NOTE: Python2 is not supported.
  * Qumulo API SDK 3.1.1 or newer installed for Python3. (aka. API Tools)
  * An SMTP server running on port TCP 25. (TLS not available.)


## Installation
To install and use this script:

  1. Use `pip` to install the Qumulo Python API tools: `pip3 install qumulo-api`.
  2. Clone this repository using `git` or download the `cluster_device_monitor.py` file.
  If you have questions cloning a repo, please see GitHub's
  [Cloning a repository](https://help.github.com/en/articles/cloning-a-repository).
  3. Use `example_config.json` as a guide to creating a `config.json` with your alerting rules.
  4. Invoke the script by running `python ./cluster_device_monitor.py` from the cloned directory.


## Configuration
At this point, it is expected that you have a functional Qumulo cluster, the API Tools installed on your machine and the `cluster_device_monitor.py` script downloaded. If this is done, you can create a `config.json` configuration file to suit your needs. The general steps are:

  1. Use `example_config.json` as a guide to creating a `config.json` with your alerting rules. The fields for this file are described after this section.
  2. Set up a `cron` job to run as often as you like to check for alerts. See [CronHowto](https://help.ubuntu.com/community/CronHowto) if you have any questions. Example command `./cluster_device_monitor.py --config /root/config.json`

The `config.json` file contains 2 stanzas and each can have multiple objects. These stanzas are groups objects of `rules` and are individually interpreted by the script. The stanzas are:

  1. Cluster Settings
     - `cluster_address` - FQDN or IP address of a cluster node.
     - `cluster_name` - A friendly name for the cluster to generate alerts for.
     - `username` - The username to access the REST API.
     - `password` - The password to access the REST API.
     - `rest_port` - The TCP port on which to access the REST API. Default of 8000.

  2. Email Settings
     - `sender` - The email address (fake or real) that the alerts should have in the 'From:' field. A suggestion is to use the cluster's name.
     - `server` - The email server or SMTP relay that will route the emails sent by the script.
     - `mail_to` - A list of email addresses that the alerts will be sent to


## Permissions
This script needs file system permissions to run. 
    - Use `chmod 777 cluster_device_monitor.py` to grant full permissions to the script file


## FAQ

  1. What if the node I have the script pointed to goes offline? 
     - If you attempt to run the script against a node that is not reachable, the script will fail to run and present an error on the terminal. If the script was already running and the node goes offline, the script should generate and send an API timeout email; this will be an indication of failure and you should check the cluster status.
  2. Will the same alert be sent for an unhealthy device if it was already sent?
     - No, the script has logic to review the previous run of the script and will not generate a new email unless a new (unhealthy) change occurs.

### Notes
The script has some limitations or caveats; they are:
  * Email server or relay must speak SMTP over port TCP 25.
  * Script must be run to alert; the recommended method is a `cron` job that runs as often as desired.
  * It will send one email alert per JSON object in the configuration file.
  * If you would like to test this on a local email server, please see [Test Email Server](#test-email-server)



## Examples
An example configuration is uploaded to this GitHub for ease of use, `example_config.json`. Use this as a template to build your own rule set. The email alerts will be similar to these:

### Node Offline Alert

```
=================== CLUSTER EVENT ALERT! ===================
Unhealthy object(s) found. See below for info and engage Qumulo Support in your preferred fashion.
Cluster name: CoffeeTime
Cluster UUID: cf83e828-7ef7-4368-a75b-3b972d10f2c6
Approx. time: 2021-06-14T16:52:03.762556351Z UTC

1 Event(s) found:
======================= NODE OFFLINE =======================
Node Number: 2
Node Status: offline
Node S/N:
Node UUID: cbdea0e3-1659-48af-b15b-e97dbbeefd04
Node Type: QVIRT
Qumulo Core Version: Qumulo Core 4.0.1
```

### Unhealthy Drive Alert
```
=================== CLUSTER EVENT ALERT! ===================
Unhealthy object(s) found. See below for info and engage Qumulo Support in your preferred fashion.
Cluster name: CoffeeTime
Cluster UUID: cf83e828-7ef7-4368-a75b-3b972d10f2c6
Approx. time: 2021-06-14T17:55:39.744139187Z UTC

1 Event(s) found:
===================== DRIVE UNHEALTHY =====================
Node Number: 3
Drive Slot: 1
Drive Status: unhealthy
Slot Type: SSD
Disk Type: SSD
Disk Model: Virtual_disk
Disk S/N:
Disk Capacity: 10467934208
```


## Test Email Server
If you do not already have an email server to use, you can create a local one using Ubuntu and some free open source utilities. To set up a test email server on a fresh install of Ubuntu 18.04:

1. Edit `/etc/hosts` file and add in your test domain name. In this case we'll be using "@localhost.com" email addresses. Therefore, what you need to add to the `/etc/hosts` file would be:
```
127.0.0.1    localhost.com
```

2. Install the actual email server `postfix` with `sudo apt-get install postfix`. When installing `postfix`, you will see two prompts:
```
General type of mail configuration: Local Only
Domain Name: localhost.com (or whatever domain you chose.)
```

3. Create a virtual "catch all" email address by creating `/etc/postfix/virtual`. Once created, add these two lines:
```
@localhost <username>
@localhost.com <username>
```

If your local UNIX username is `testuser1` then replace `<username>` with that.

4. Modify the `postfix` configuration to allow virtual aliases. To do so add the following line to `/etc/postfix/main.cf`:
```
virtual_alias_maps = hash:/etc/postfix/virtual
```

NOTE: It is good practice to back up the `main.cf` configuration before making changes.

5. Run `sudo postmap /etc/postfix/virtual` to activate.

6. Reload `postfix` so that the above changes apply. To do so:
    `sudo service postfix reload`

7. Test that you are able to send an email! From the same client running the `postfix` server, run the following commands one at a time, and pressing <ENTER> after each one:
```
telnet localhost 25
helo localhost.com (or whatever domain you chose in step 2)
mail from: testuser1@localhost.com
rcpt to: doesntexist@localhost.com (this step will fail if step 4 & 5 were not done)
data
write something here
. (Just a period, and you should see a Queued message after this.)
quit
```

If all the steps above completed successfully, you should see something like this:
```
    qumulotest:src$ telnet localhost 25
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    220 qumulotest.eng.qumulo.com ESMTP Postfix (Ubuntu)
    helo localhost.com
    250 qumulotest.eng.qumulo.com
    mail from: testuser1@localhost.com
    250 2.1.0 Ok
    rcpt to: bogusemail@localhost.com
    250 2.1.5 Ok
    data
    354 End data with <CR><LF>.<CR><LF>
    something in the body of the email
    .
    250 2.0.0 Ok: queued as 1E46BCA00D7
    quit
    221 2.0.0 Bye
    Connection closed by foreign host.
```

8. Install `mailutils` so that you can see if you're getting email:
    `sudo apt install mailutils`

    Once installed, just run `mail` to see if you were able to get the test email. Alternatively, you can try and `cat /var/spool/mail/<username>`.


If something went wrong and you'd like to retry, uninstall everything with:
```
sudo apt-get remove postfix
sudo apt-get purge postfix
```

Then reinstall `postfix` with:
    `sudo apt-get install postfix`
