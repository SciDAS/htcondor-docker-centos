#!/bin/bash
#
# Install Docker, Mesos and Kubernetes on Ubuntu (trusty, xenial)
#
# Author: Fan Jiang
#
set +ex

usage() {
  cat <<-EOF
  Usage: $0 -h <master-public-ip> [-n <num-cores>]

  Install Docker, Mesos and Marathon on Ubuntu server

  Options:
      -h <master-ip-addr>: public IP address of the Mesos master
      -n <num-cores>: number of cores for compiling Mesos source code
EOF
  exit 1
}

MESOS_VERSION=1.3.1

while getopts h:n OPT;do
    case "${OPT}" in
        h) IP=${OPTARG};;
        n) NUM_CORES=${OPTARG};;
    esac
done

[ ! ${IP} ] && usage
NUM_CORES=${NUM_CORES:=4}


echo -ne "${IP}\t$(hostname)" | sudo tee -a /etc/hosts
sudo hostname $(hostname)

# install docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-get install -y software-properties-common python-software-properties
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce
sudo usermod -aG docker ${USER}

# install mesos
sudo apt-get install -y tar wget git openjdk-8-jdk build-essential python-dev \
    python-six python-virtualenv libcurl4-nss-dev libsasl2-dev libsasl2-modules \
    maven libapr1-dev libsvn-dev zlib1g-dev golang
wget http://www.apache.org/dist/mesos/${MESOS_VERSION}/mesos-${MESOS_VERSION}.tar.gz
tar -zxf mesos-${MESOS_VERSION}.tar.gz
mkdir mesos-${MESOS_VERSION}/build
cd mesos-${MESOS_VERSION}/build
../configure
sudo make -j$NUM_CORES
sudo make install
cd ${HOME}
echo 'export MESOS_NATIVE_JAVA_LIBRARY=/usr/local/lib/libmesos.so' >> ${HOME}/.bashrc
source ${HOME}/.bashrc

# install zookeeper
sudo apt-get install -y zookeeperd

# start mesos master
sudo nohup ${HOME}/mesos-${MESOS_VERSION}/build/bin/mesos-master.sh \
          --ip=0.0.0.0 \
          --work_dir=/var/lib/mesos \
          --zk=zk://$IP:2181/mesos \
          --quorum=1 --advertise_ip=$IP > ${HOME}/master.log &

# start mesos agent
sudo nohup ${HOME}/mesos-${MESOS_VERSION}/build/bin/mesos-agent.sh \
        --master=$IP:5050 \
        --work_dir=/var/lib/mesos \
        --containerizers=mesos,docker > ${HOME}/agent.log &

# install Kubernetes on Mesos
git clone https://github.com/kubernetes-incubator/kube-mesos-framework
cd kube-mesos-framework
sudo make -j${NUM_CORES}
cd ${HOME}

KUBE_HOME=${HOME}/kube-mesos-framework
KM=${HOME}/kube-mesos-framework/_output/local/go/bin/km

KUBERNETES_MASTER_IP=${IP}
KUBERNETES_MASTER=http://${KUBERNETES_MASTER_IP}:8888
MESOS_MASTER=zk://${IP}:2181/mesos

cat >> ${HOME}/.bashrc <<EOF
export KUBERNETES_MASTER_IP=${IP}
export KUBERNETES_MASTER=http://${KUBERNETES_MASTER_IP}:8888
export PATH=${HOME}/kube-mesos-framework/_output/local/go/bin:\$PATH
export MESOS_MASTER=zk://${IP}:2181/mesos
EOF
source ${HOME}/.bashrc

# start etcd
sudo docker run -d --hostname $(uname -n) --name etcd \
  -p 4001:4001 -p 7001:7001 quay.io/coreos/etcd:v2.2.1 \
  --listen-client-urls http://0.0.0.0:4001 \
  --advertise-client-urls http://${KUBERNETES_MASTER_IP}:4001

cat <<EOF > ${KUBE_HOME}/mesos-cloud.conf
[mesos-cloud]
        mesos-master        = ${MESOS_MASTER}
EOF

# start Kubernetes
nohup $KM apiserver \
  --address=0.0.0.0 \
  --etcd-servers=http://${KUBERNETES_MASTER_IP}:4001 \
  --service-cluster-ip-range=10.10.10.0/24 \
  --port=8888 \
  --cloud-provider=mesos \
  --cloud-config=${KUBE_HOME}/mesos-cloud.conf \
  --secure-port=0 \
  --v=1 > ${HOME}/apiserver.log &

nohup $KM controller-manager \
  --master=${KUBERNETES_MASTER_IP}:8888 \
  --cloud-provider=mesos \
  --cloud-config=${KUBE_HOME}/mesos-cloud.conf  \
  --v=1 > ${HOME}/controller.log &

sleep 5

nohup $KM scheduler \
  --address=0.0.0.0 \
  --mesos-master=${MESOS_MASTER} \
  --etcd-servers=http://${KUBERNETES_MASTER_IP}:4001 \
  --mesos-user=root \
  --api-servers=${KUBERNETES_MASTER_IP}:8888 \
  --cluster-dns=8.8.8.8 \
  --cluster-domain=cluster.local \
  --v=2 > ${HOME}/scheduler.log  &

# install kubectl
curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
chmod +x kubectl
sudo mv kubectl /usr/local/bin
