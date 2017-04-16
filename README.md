prox-provision
====

This script is a "dirty" version of cloud-init, specifically made for use with
prox-scheduler, proxmox, and was designed to run on Debian 8.0 x64.

Usage
----
 1. Follow "Proxmox Setup" Guide
 2. Follow "Image Setup" Guide

Proxmox Setup
----
  * Create a custom Proxmox group & user for this service to use
  
  ```
  pveum roleadd PVECloudInit -privs "VM.Config.Options VM.Audit"
  pveum groupadd CloudInit -comment "API User Group"
  pveum aclmod / -group CloudInit -role PVECloudInit
  pveum useradd CloudInit@pve -comment "CloudInit API User"
  pveum passwd CloudInit@pve
  pveum usermod CloudInit@pve -group CloudInit
  ```

Image Setup
----
  1. Create Debian 8.0 x64 VM in Proxmox
  2. Run the following commands to install dependencies
  
    
    apt-get update
    apt-get install build-essential python3 python3-dev libffi-dev libssl-dev
    wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
    chmod +x /tmp/get-pip.py
    python3 /tmp/get-pip.py
    
    
  3. Install this script
  
    
    pip3 install -r ./src/requires.txt
    cp ./src/prox-provision.py /usr/sbin/prox-provision
    chmod +x /usr/sbin/prox-provision
    cp ./src/prox-provision.initd /etc/init.d/prox-provision
    chmod a+x /etc/init.d/prox-provision
    mkdir -p /etc/prox-provision
    cp ./src/settings.conf.example /etc/prox-provision/settings.conf
    cp ./src/prox-provision.initd.default.example /etc/default/prox-provision
    insserv /etc/init.d/prox-provision
    
    
  4. Exit our provision settings & init script settings to match our requirements
  
    
    nano /etc/prox-provision/settings.conf
    nano /etc/default/prox-provision
    
    
  5. Shutdown instance, convert to template, and test!

To Do
----
  * Move to external User Data provider in prox-scheduler (REST Endpoint)
