#!/bin/bash
#
# Install Docker, Mesos and Marathon on Ubuntu (trusty, xenial)
#
# Author: Fan Jiang
#
set +ex

usage() {
  cat <<-EOF
  Usage: $0 -h <master-public-ip> [-p <peer-list>] [-n <num-cores>]

  Install Docker, Mesos and Marathon on Ubuntu server

  Options:
      -h <master-ip-addr>: public IP address of the Mesos master
      -p <peer-list>: a comma-separated list of public IP addresses of peer hosts
      -n <num-cores>: number of cores for compiling Mesos source code
EOF
  exit 1
}

MESOS_VERSION=1.3.1

while getopts h:p:n OPT;do
    case "${OPT}" in
        h) IP=${OPTARG};;
        p) PEERS=$(echo ${OPTARG} | tr ',' ' ');;
        n) NUM_CORES=${OPTARG};;
    esac
done

[ ! ${IP} ] && usage
NUM_CORES=${NUM_CORES:=4}

# install curl
sudo apt-get update
sudo apt-get install -y curl

# install docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-get install -y software-properties-common python-software-properties
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce

# install mesos
sudo apt-get install -y tar wget git openjdk-8-jdk build-essential python-dev \
    python-six python-virtualenv libcurl4-nss-dev libsasl2-dev libsasl2-modules \
    maven libapr1-dev libsvn-dev zlib1g-dev
wget http://www.apache.org/dist/mesos/${MESOS_VERSION}/mesos-${MESOS_VERSION}.tar.gz
tar -zxf mesos-${MESOS_VERSION}.tar.gz
mkdir mesos-${MESOS_VERSION}/build
cd mesos-${MESOS_VERSION}/build
../configure
sudo make -j$NUM_CORES
sudo make install
cd ~
echo 'export MESOS_NATIVE_JAVA_LIBRARY=/usr/local/lib/libmesos.so' >> ~/.profile
source ~/.profile

# install weave
sudo curl -L git.io/weave -o /usr/local/bin/weave
sudo chmod a+x /usr/local/bin/weave
sudo weave launch --ipalloc-range=172.20.0.0/20
if [ -n "$PEERS" ];then
    sudo weave connect $PEERS
fi

# install zookeeper
sudo apt-get install -y zookeeperd

# install marathon
curl -O http://downloads.mesosphere.com/marathon/v1.4.3/marathon-1.4.3.tgz
tar xzf marathon-1.4.3.tgz

# start mesos master
sudo nohup ~/mesos-${MESOS_VERSION}/build/bin/mesos-master.sh \
          --ip=0.0.0.0 \
          --work_dir=/var/lib/mesos \
          --zk=zk://$IP:2181/mesos \
          --quorum=1 --advertise_ip=$IP > ~/master.log &
# start marathon
sudo nohup ~/marathon-1.4.3/bin/start \
    --master zk://$IP:2181/mesos \
    --zk zk://$IP:2181/marathon > ~/marathon.log &

# start mesos agent
sudo nohup env MESOS_DOCKER_SOCKET=/var/run/weave/weave.sock \
  ~/mesos-${MESOS_VERSION}/build/bin/mesos-agent.sh \
        --master=$IP:5050 \
        --work_dir=/var/lib/mesos \
        --containerizers=mesos,docker > ~/agent.log &


