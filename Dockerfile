# vim: ft=Dockerfile :

FROM centos:7
MAINTAINER Matteo Panella <matteo.panella@cnaf.infn.it>
ENV TINI_VERSION v0.9.0

COPY htcondor-stable-rhel7.repo /etc/yum.repos.d/

RUN set -ex \
        && mkdir -p /var/run/lock \
        && yum makecache fast \
        && yum --disablerepo=htcondor-stable -y install wget epel-release \
        && wget -qO /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor \
        && rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor \
        && wget -qO /sbin/tini https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini \
        && chmod +x /sbin/tini \
        && yum -y remove wget \
        && yum -y install condor supervisor \
        && yum clean all

COPY supervisord.conf /etc/supervisord.conf
COPY condor.ini /etc/supervisord.d/condor.ini
COPY condor-wrapper.sh /usr/local/sbin/condor-wrapper.sh
COPY condor_config /etc/condor/condor_config
COPY run.sh /usr/local/sbin/run.sh

RUN useradd -m -s /bin/bash condor_pool

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/sbin/run.sh"]
