#!/bin/bash

# start in the docker directory
cd "$( dirname "$0" )"
HTCONDOR_CONFIG_DIR="$( pwd )"

DOCKER_NAME_MASTER="condor-master"
DOCKER_NAME_SUBMITTER="condor-submitter"
DOCKER_NAME_EXECUTOR="condor-executor"

DOCKER_NET_NAME="htcondor"
DOCKER_HTCONDOR_IMAGE="scidas/htcondor-centos"
DOCKER_PEGASUS_HTCONDOR_IMAGE="scidas/pegasus-condor-submitter"
DOCKER_HTCONDOR_IMAGE_TAG="latest"

HTCONDOR_FLOCKING_ONLY=false

# password file for HTCondor security
# the password file must be owned by root, with permission 600 (rw-------)
HOST_PASSWORD_FILE=${HTCONDOR_CONFIG_DIR}/pool_password
CONTAINER_PASSWORD_FILE=/var/lib/condor/pool_password
if [ ! -e ${HOST_PASSWORD_FILE} ]
then 
  echo "ERROR: password file ${HOST_PASSWORD_FILE} must be present"
  exit 1
fi
if [ $(stat -c %a ${HOST_PASSWORD_FILE} ) != "600" ]
then
  echo "ERROR: password file ${HOST_PASSWORD_FILE} must have permissions 600 (rw-------)"
  exit 1
fi
if [ $(stat -c %U ${HOST_PASSWORD_FILE} ) != "root" ]
then
  echo "ERROR: password file ${HOST_PASSWORD_FILE} must owned by root"
  exit 1
fi

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -t|--tag-name)
      DOCKER_HTCONDOR_IMAGE_TAG="$2"
      shift # past argument
      ;;
    -f)
      #echo "found flocking option"
      HTCONDOR_FLOCKING_ONLY=true
      ;;
    *)
      # unknown option
      echo "unknown option $1"
      exit 1
      ;;
esac
shift # past argument or value
done

# remove stopped or running containers
f_rm_f_docker_container ()
{
  #container_name="$1"
  RUNNING=$(docker inspect --format="{{ .State.Running }}" $1 2> /dev/null)

  # if it's not there at all, we don't need to remove it
  if [ $? -ne 1 ]; then
    echo -n "Removing container: "
    docker rm -f $1

    # check exit status, and kill script if not successful
    if [ $? -ne 0 ]
    then
      exit $?
    fi
  fi
}

# Remove any previous docker containers of name
echo "Info: removing any previous HTCondor containers..."
f_rm_f_docker_container ${DOCKER_NAME_EXECUTOR}
f_rm_f_docker_container ${DOCKER_NAME_SUBMITTER}
f_rm_f_docker_container ${DOCKER_NAME_MASTER}

# Create docker network
NET_INSPECT=$(docker network inspect ${DOCKER_NET_NAME} 2> /dev/null)
# only create it if it doesn't already exist
if [ $? -eq 1 ]; then
  echo -n "Creating docker network ${DOCKER_NET_NAME}: "
  docker network create ${DOCKER_NET_NAME}
else
  echo "Info: Docker network '${DOCKER_NET_NAME}' already exists."
fi

# Docker-on-Mac is a bit slower
var_sleep=5
if [[ $OSTYPE == darwin* ]]
then
  let "var_sleep *= 15"
fi

# Start HTCondor Master
#if [ "$HTCONDOR_FLOCKING_ONLY" = true ]
#then
  #echo "Flocking only, will not run ${DOCKER_NAME_MASTER}"
#else
  echo -n "docker run ${DOCKER_NAME_MASTER}:${DOCKER_HTCONDOR_IMAGE_TAG} "
             #--publish 127.0.0.1:8080:8080 \
  docker run -d \
             --net ${DOCKER_NET_NAME} \
             --name ${DOCKER_NAME_MASTER} \
             --hostname ${DOCKER_NAME_MASTER} \
             --volume ${HTCONDOR_CONFIG_DIR}/config.d/:/etc/condor/config.d \
             --volume ${HOST_PASSWORD_FILE}:${CONTAINER_PASSWORD_FILE} \
             --publish 8080 \
             ${DOCKER_HTCONDOR_IMAGE}:${DOCKER_HTCONDOR_IMAGE_TAG} \
             -m #start as master

  # check exit status from docker run, and kill script if not successful
  if [ $? -ne 0 ]
  then
    exit $?
  fi

  # Sleep
  echo -n "Sleeping for ${var_sleep} to allow ${DOCKER_NAME_MASTER} container to start ..."
  sleep ${var_sleep};
  echo " done."
#fi

# Start HTCondor Submitter
echo -n "docker run ${DOCKER_NAME_SUBMITTER}:${DOCKER_HTCONDOR_IMAGE_TAG} "
           #--publish 127.0.0.1:8081:8080 \ #SOAP
           #--publish 8080 \ #SOAP
           #--hostname ${DOCKER_NAME_SUBMITTER} \
           #--hostname proof-of-concept.scidas.renci.org \
           #--net=host \
docker run -d \
           --net ${DOCKER_NET_NAME} \
           --name ${DOCKER_NAME_SUBMITTER} \
           --hostname ${DOCKER_NAME_SUBMITTER} \
           --volume ${HTCONDOR_CONFIG_DIR}/condor_config.local.submitter:/etc/condor/condor_config.local \
           --volume ${HTCONDOR_CONFIG_DIR}/config.d/:/etc/condor/config.d \
           --volume ${HTCONDOR_CONFIG_DIR}/probe/ProbeConfig:/etc/gratia/condor/ProbeConfig \
           --volume ${HTCONDOR_CONFIG_DIR}/probe/hostkey.pem:/etc/grid-security/hostkey.pem \
           --volume ${HTCONDOR_CONFIG_DIR}/probe/hostcert.pem:/etc/grid-security/hostcert.pem \
           --volume ${HTCONDOR_CONFIG_DIR}/probe/certificates/:/etc/grid-security/certificates/ \
           --volume ${HOST_PASSWORD_FILE}:${CONTAINER_PASSWORD_FILE} \
           --publish 9618:9618 \
           ${DOCKER_PEGASUS_HTCONDOR_IMAGE}:${DOCKER_HTCONDOR_IMAGE_TAG} \
           -s ${DOCKER_NAME_MASTER}

# check exit status from docker run, and kill script if not successful
if [ $? -ne 0 ]
then
  exit $?
fi

# Sleep
let "var_sleep /= 2";
echo -n "Sleeping for ${var_sleep} to allow ${DOCKER_NAME_SUBMITTER} container to start ..."
sleep ${var_sleep};
echo " done."

# Start HTCondor Executor
if [ "$HTCONDOR_FLOCKING_ONLY" = true ]
then
  echo "Flocking only, will not run ${DOCKER_NAME_EXECUTOR}"
else
  echo -n "docker run ${DOCKER_NAME_EXECUTOR}:${DOCKER_HTCONDOR_IMAGE_TAG} "
  docker run -d \
             --net ${DOCKER_NET_NAME} \
             --name ${DOCKER_NAME_EXECUTOR} \
             --hostname ${DOCKER_NAME_EXECUTOR} \
             --volume ${HTCONDOR_CONFIG_DIR}/config.d/:/etc/condor/config.d \
             --volume ${HOST_PASSWORD_FILE}:${CONTAINER_PASSWORD_FILE} \
             ${DOCKER_HTCONDOR_IMAGE}:${DOCKER_HTCONDOR_IMAGE_TAG} \
             -e ${DOCKER_NAME_MASTER}

  # check exit status from docker run, and kill script if not successful
  if [ $? -ne 0 ]
  then
    exit $?
  fi
fi

echo "Note: You will probably need to wait 60 seconds for HTCondor to finish starting up."

