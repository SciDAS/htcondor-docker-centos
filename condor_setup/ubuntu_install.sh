#!/bin/bash

# Script for installing HTCondor on Ubuntu 14.04 with Flocking mode on
# 
# The script defaults to a low security level and should only be used for development and test. 
# More sophisticated security configuration should be done for the production environment. 
#
# @author: Fan Jiang (dcvan@renci.org)

set -ex
condor_config=/etc/condor/condor_config
host_ip_addr=$1
flock_from_list=$2 # comma-separated list 

echo 'deb http://research.cs.wisc.edu/htcondor/ubuntu/stable/ trusty contrib' | sudo tee -a /etc/apt/sources.list
wget -qO - http://research.cs.wisc.edu/htcondor/ubuntu/HTCondor-Release.gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y condor

sudo sed -i "/^.*$(hostname).*$/d" /etc/hosts
echo "$host_ip_addr $(hostname)" | sudo tee -a /etc/hosts

echo 'ALLOW_READ=*' | sudo tee -a ${condor_config}
echo 'ALLOW_WRITE=*' | sudo tee -a ${condor_config}
echo "FLOCK_FROM=${flock_from_list}" | sudo tee -a ${condor_config}
echo 'SEC_DEFAULT_AUTHENTICATION_METHODS = CLAIMTOBE' | sudo tee -a ${condor_config}

sudo service condor restart
