FROM centos:7
MAINTAINER Fan Jiang <dcvan@renci.org>

ARG TINI_VERSION=v0.9.0
ARG GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py

COPY condor/htcondor-stable-rhel7.repo /etc/yum.repos.d/

RUN set -ex \
	&& mkdir -p /var/run/lock \
	&& yum makecache fast \
	&& yum --disablerepo=htcondor-stable -y install wget epel-release \
    && wget -qO /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor \
    && rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor \
	&& wget -qO /sbin/tini https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini \
    && chmod +x /sbin/tini \
	&& wget -O /etc/yum.repos.d/pegasus.repo http://download.pegasus.isi.edu/wms/download/rhel/7/pegasus.repo \
	&& yum install -y pegasus \
	&& yum install -y /tmp/osg-3.3-el7-release-latest.rpm https://repo.grid.iu.edu/osg/3.3/osg-3.3-el7-release-latest.rpm \
    && yum install -y gratia-probe-glideinwms cronie \
    && sed -i '/session required pam_loginuid.so/d' /etc/pam.d/crond \
    && yum -y install fuse-libs openssl \
    && wget -qO /root/icommands.rpm ftp://ftp.renci.org/pub/irods/releases/4.1.10/centos7/irods-icommands-4.1.10-centos7-x86_64.rpm \
    && rpm -i /root/icommands.rpm \
    && rm -f /root/icommands.rpm \
	&& yum remove -y wget \
	&& yum install -y git vim gettext supervisor condor openssh-server openssh-clients \
	&& yum clean all

# install python3.6
RUN yum -y update \
    && yum -y install https://centos7.iuscommunity.org/ius-release.rpm \
    && yum -y install python36u python36u-devel gcc net-tools\
    && ln -s /usr/bin/python3.6 /usr/bin/python3 \
    && curl -O $GET_PIP_URL \
    && python3 get-pip.py \
    && rm -f get-pip.py \
    && pip3 install requests netifaces \
    && yum clean all

RUN /usr/bin/ssh-keygen -A
RUN useradd -m -s /bin/bash condor_pool

COPY keys/workflow /home/condor_pool/.ssh/workflow
COPY keys/workflow.pub /home/condor_pool/.ssh/workflow.pub
COPY keys/workflow.pub /home/condor_pool/.ssh/authorized_keys

RUN su - condor_pool -c 'mkdir -p /home/condor_pool/.irods'
RUN chmod 600 /home/condor_pool/.ssh/workflow
RUN chmod 644 /home/condor_pool/.ssh/workflow.pub
RUN chmod 644 /home/condor_pool/.ssh/authorized_keys
RUN chown -R condor_pool:condor_pool /home/condor_pool/.ssh

COPY supervisord/supervisord.conf /etc/supervisord.conf
COPY supervisord/condor.ini /etc/supervisord.d/condor.ini
COPY supervisord/sshd.ini /etc/supervisord.d/sshd.ini

COPY OSG-KINC /home/condor_pool/OSG-KINC
RUN chown -R condor_pool:condor_pool /home/condor_pool/OSG-KINC
RUN mkdir -m 744 /local-scratch
RUN mkdir /etc/grid-security
RUN chown -R condor_pool:condor_pool /local-scratch

COPY condor/condor-wrapper.sh /usr/local/sbin/condor-wrapper.sh
COPY condor/condor_config /etc/condor/condor_config
COPY condor/condor_config.local /etc/condor/condor_config.local
ADD condor/config.d /etc/condor/config.d

COPY run.py /usr/local/sbin/run.py

RUN chmod +x /usr/local/sbin/run.py
RUN chmod +x /usr/local/sbin/condor-wrapper.sh

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/sbin/run.py"]
