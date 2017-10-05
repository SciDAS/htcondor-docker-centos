#!/usr/bin/env bash

TYPE=$1

sudo yum install -y wget vim bind-utils ntp

# load overlay module
sudo tee /etc/modules-load.d/overlay.conf <<-'EOF'
overlay
EOF
sudo modprobe overlay

# add docker repo
sudo tee /etc/yum.repos.d/docker.repo <<-'EOF'
[dockerrepo]
name=Docker Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/$releasever/
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
EOF

# add systemd entry
sudo mkdir -p /etc/systemd/system/docker.service.d && sudo tee /etc/systemd/system/docker.service.d/override.conf <<- EOF
[Service]
ExecStart=
ExecStart=/usr/bin/docker daemon --storage-driver=overlay -H fd://
EOF

sudo yum install -y --tolerant docker-engine-1.11.0

sudo systemctl start docker
sudo usermod -aG docker $USER


if [ "$TYPE" == bootstrap ]; then
    # Bootstrap
    curl -O https://downloads.dcos.io/dcos/EarlyAccess/commit/14509fe1e7899f439527fb39867194c7a425c771/dcos_generate_config.sh
else
    # Mesos agent
    sudo yum install -y tar xz unzip curl ipset
    sudo groupadd nogroup
fi

