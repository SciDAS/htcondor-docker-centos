#!/bin/bash

echo "NUM_SLOTS=$1" >> /etc/condor/condor_config.local
exec /usr/bin/supervisord -c /etc/supervisord.conf

