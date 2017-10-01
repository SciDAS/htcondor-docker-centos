#!/bin/bash

echo "FLOCK_TO=$1" >> /etc/condor/condor_config.local
echo "export HOSTNAME=$(ip addr show ethwe | grep -Po 'inet \K[\d.]+')" >> /etc/profile
source /etc/profile
exec /usr/bin/supervisord -c /etc/supervisord.conf

