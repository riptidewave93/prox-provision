#!/usr/bin/env python3
#
# Basic oneshot Cloud-Init script for running on Proxmox.
#
# Copyright (C) 2016-2017 Chris Blake <chris@servernetworktech.com>
#
import configparser
import netifaces
import os
from proxmoxer import ProxmoxAPI
import re
import subprocess
import sys

# Try to load in our settigns file
config = configparser.ConfigParser()
try:
    config.read('/etc/prox-provision/settings.conf')
except Exception as e:
    raise Exception('Error loading our config file. Error returned: ' + str(e))

# Set our Settings
prox_url=config['Proxmox']['URL']
prox_user=config['Proxmox']['User']
prox_pass=config['Proxmox']['Password']
ud_start_flag=config['User-Data']['StartFlag']
ud_end_flag=config['User-Data']['EndFlag']

# Function to itterate for line count in a files
def file_len(fname):
    with open(fname) as f:
        i=-1
        for i, l in enumerate(f):
            pass
    return i + 1

# Used to set our hostname
def SetHostname(nhn):
    # get our current hostname (for parsing)
    ohn = str(subprocess.check_output("hostname -f", shell=True).decode("utf-8")).strip("\n")

    # Replace hostname in core files
    os.system('sed -i \'s|' + ohn + '|' + nhn + '|g\' /etc/hostname')
    os.system('sed -i \'s|' + ohn + '|' + nhn + '|g\' /etc/hosts')

    # Reload hostname
    os.system('hostname -F /etc/hostname')

    # Return system advertised hostname, in full
    return str(subprocess.check_output("hostname -f", shell=True).decode("utf-8")).strip("\n")

# Used to parse & save our userdata
def ParseUserData(proxmox, nodeid, instance, ip):
    # We have our instance, but we need our config. Let's get that
    config = proxmox.nodes(nodeid).qemu(instance['vmid']).config.get()

    # First, check if our key exists
    if "description" in config:
        if ud_start_flag in config['description'] and ud_end_flag in config['description']:
            with open("/tmp/cloud-init.sh", 'a') as out:
                out.write(config['description'].rpartition(ud_end_flag)[0].rpartition(ud_start_flag)[2])
            os.system('chmod +x /tmp/cloud-init.sh')

            # Now that we have done our part, remove the userdata from the desc for privacy purposes
            newdesc = re.sub(r'' + ud_start_flag + '.*?' + ud_end_flag, '', config['description'], flags=re.DOTALL) + "IP = " + str(ip)
            proxmox.nodes(nodeid).qemu(instance['vmid']).config.put(description=newdesc)

            return True
        else:
            # No userdata, but we still need to add our IP to the description
            newdesc = config['description'] + "\nIP = " + str(ip)
            proxmox.nodes(nodeid).qemu(instance['vmid']).config.put(description=newdesc)

            return False

# Used to enable pass change if no SSH key is applied
def SSHKeyCheck(ssh_keys):
    # get our authorized_keys file if it exists.
    if os.path.isfile("/root/.ssh/authorized_keys"):
        # Check if we have a key added
        if file_len('/root/.ssh/authorized_keys') == ssh_keys:
            # No added keys, disable
            os.system('chage -d 0 root')
        else:
            # We have a new key, so remove pass
            os.system('passwd root -d')
    else:
        # No file, disable
        os.system('chage -d 0 root')


# Get the mac of eth0 (as we always have this int)
mac = netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr'].upper()
ip = netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']

# Before we get started, have we ran already?
if os.path.isfile('/etc/prox-provision/.mac'):
    filez = open('/etc/prox-provision/.mac', 'r')
    macfile = filez.read()
    if str(mac) in macfile:
        sys.exit(1)

# Configure API call information
proxmox = ProxmoxAPI(prox_url, user=prox_user,
                     password=prox_pass, verify_ssl=False)

# Vars to hold our instance and node ID
instance=None
nodeid=None

# For each node
for node in proxmox.cluster.resources.get(type='node'):
    if instance != None:
        break
    # For each VM
    for vm in proxmox.nodes(node['node']).qemu.get():
        if instance != None:
            break
        # For each VM config (can't be tied to above call (GAY!))
        vmconfig = proxmox.nodes(node['node']).qemu(vm['vmid']).config.get()
        # Parse out net info only!
        for key in vmconfig.keys():
            if instance != None:
                break
            if "net" in key:
                # Did we find our MAC?
                if mac in vmconfig[key]:
                    # Save our insance for parsing
                    instance = vm
                    nodeid=node['node']
                    break

# If we were found, do our thing.
if instance != None:
    # Configure our hostname
    hostname = SetHostname(instance['name'])

    # Configure our userdata (if we have any)
    userdata = ParseUserData(proxmox, nodeid, instance, ip)

    # Set hostname and verify
    if instance['name'] not in hostname:
        os.system('echo "\n\nError with provision!\nOur IP is: ' + ip + '" > /dev/console')
        sys.exit(1)
    else:
        # Before we run userdata, check for any SSH keys and count
        ssh_keys = 0
        if os.path.isfile("/root/.ssh/authorized_keys"):
            ssh_keys = file_len('/root/.ssh/authorized_keys')

        # Run our userdata if we need to
        if userdata:
            os.system('bash /tmp/cloud-init.sh | tee /var/log/cloud-init-output.log > /dev/console 2>&1')

        # Check for any new keys before forcing a root pw reset
        SSHKeyCheck(ssh_keys)

        # All good, let's clear console a bit and print out our IP for peoplez
        os.system('sleep 5 && echo "\n\nOur IP is: ' + ip + '" > /dev/console')

        # Save our MAC to a file
        f = open('/etc/prox-provision/.mac', 'w')
        f.write(str(mac))
        f.close()

        # Exit out
        sys.exit(0)
else:
    os.system('echo "\n\nError with provision!\nOur IP is: ' + ip + '" > /dev/console')
    sys.exit(1)
