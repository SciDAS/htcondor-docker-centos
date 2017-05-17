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

COPY supervisord/supervisord.conf /etc/supervisord.conf
COPY supervisord/condor.ini /etc/supervisord.d/condor.ini
COPY condor-wrapper.sh /usr/local/sbin/condor-wrapper.sh
COPY condor_config /etc/condor/condor_config
COPY run.sh /usr/local/sbin/run.sh

# 'condor_pool' user needed for remote Python API access
RUN useradd -m -s /bin/bash condor_pool

# Account probe, needed for Flocking to OSG
# https://twiki.grid.iu.edu/bin/view/Accounting/ProbeConfigGlideinWMS
    #rpm -Uvh https://repo.grid.iu.edu/osg/3.3/osg-3.3-el7-release-latest.rpm && \
# https://github.com/CentOS/CentOS-Dockerfiles/issues/31
RUN yum -y install yum-plugin-priorities wget && \
    yum clean all && \
    wget -qO /tmp/osg-3.3-el7-release-latest.rpm https://repo.grid.iu.edu/osg/3.3/osg-3.3-el7-release-latest.rpm && \
    yum -y install /tmp/osg-3.3-el7-release-latest.rpm && \
    yum -y install gratia-probe-glideinwms cronie && \
    yum -y remove wget && \
    yum clean all && \
    sed -i '/session required pam_loginuid.so/d' /etc/pam.d/crond

COPY supervisord/crond.ini /etc/supervisord.d/crond.ini

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/sbin/run.sh"]
