#!/bin/bash

usage() {
  cat <<-EOF
  Usage: $0  -u <irods-user> -p <irods-password> [-m <master-host>]
            [-h <icat-host>] [-P <irods-port>] [-z <irods-zone>]

  Initial setup of HTCondor pool

  Options:
      -u <irods-user>: iRODS user
      -p <irods-password>: iRODS password
      -m <master-host>: HTCondor master host; runs as a worker if set
      -h <icat-host>: iCAT host
      -P <irods-port> iCAT port number
      -z <irods-zone> iRODS zone
EOF
  exit 1
}

while getopts u:p:m:h:P:z OPT;do
    case "${OPT}" in
        u) IRODS_USER=${OPTARG};;
        p) IRODS_PW=${OPTARG};;
        m) MASTER_HOST=${OPTARG};;
        h) IRODS_HOST=${OPTARG};;
        P) IRODS_PORT=${OPTARG};;
        z) IRODS_ZONE=${OPTARG};;
    esac
done

[ ! ${IRODS_USER} -o ! ${IRODS_PW} ] && usage

IRODS_HOST=${IRODS_HOST:='irods-renci.scidas.org'}
IRODS_PORT=${IRODS_PORT:=1247}
IRODS_ZONE=${IRODS_ZONE:='scidasZone'}

# configure HTCondor
if [ -z ${MASTER_HOST} ];then
cat >> /etc/condor/condor_config.local <<EOF
CONDOR_HOST = \$(FULL_HOSTNAME)
DAEMON_LIST = MASTER, NEGOTIATOR, COLLECTOR, SCHEDD, STARTD
NUM_SLOTS = ${SCIDAS_RESC_CPUS}
FLOCK_FROM = ${SCIDAS_APP_NETWORK}
EOF
else
cat >> /etc/condor/condor_config.local <<EOF
CONDOR_HOST = ${MASTER_HOST}
DAEMON_LIST = MASTER, STARTD
NUM_SLOTS = ${SCIDAS_RESC_CPUS}
EOF
fi

# create iCommands environment file
cat > /home/condor_pool/.irods/irods_environment.json <<EOF
{
    "irods_host": "${IRODS_HOST}",
    "irods_port": ${IRODS_PORT},
    "irods_user_name": "${IRODS_USER}",
    "irods_zone_name": "${IRODS_ZONE}",
    "irods_password": "${IRODS_PW}",
    "irods_client_server_negotiation": "request_server_negotiation",
    "irods_client_server_policy": "CS_NEG_REFUSE",
    "irods_encryption_key_size": 32,
    "irods_encryption_salt_size": 8,
    "irods_encryption_num_hash_rounds": 16,
    "irods_encryption_algorithm": "AES-256-CBC",
    "irods_default_hash_scheme": "SHA256",
    "irods_match_hash_policy": "compatible"
}
EOF
chown condor_pool /home/condor_pool/.irods/irods_environment.json
chmod 0600 /home/condor_pool/.irods/irods_environment.json
su - condor_pool -c "iinit ${IRODS_PW}"

exec /usr/bin/supervisord -c /etc/supervisord.conf

