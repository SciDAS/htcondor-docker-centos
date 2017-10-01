FROM centos:7
MAINTAINER Fan Jiang <dcvan@renci.org>

ENV TINI_VERSION v0.9.0

COPY condor/htcondor-stable-rhel7.repo /etc/yum.repos.d/

RUN set -ex \
	&& mkdir -p /var/run/lock \
	&& yum makecache fast \
	&& yum --disablerepo=htcondor-stable -y install wget epel-release \
        && wget -qO /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor \
        && rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-HTCondor \
	&& wget -qO /sbin/tini https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini \
        && chmod +x /sbin/tini \
	&& yum remove -y wget \
	&& yum install -y supervisor condor openssh-server openssh-clients \
	&& yum install -y autofs fuse \
	&& yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm \
	&& yum install -y yum-plugin-priorities \
	&& yum install -y https://repo.grid.iu.edu/osg/3.4/osg-3.4-el7-release-latest.rpm \
	&& yum install -y osg-oasis \
	&& echo "user_allow_other" >> /etc/fuse.conf \
	&& echo "/cvmfs /etc/auto.cvmfs" >> /etc/auto.master \
	&& chmod 4755 /bin/fusermount \
	&& yum clean all 

RUN /usr/bin/ssh-keygen -A
RUN useradd -m -s /bin/bash condor_pool

COPY keys/workflow /home/condor_pool/.ssh/workflow
COPY keys/workflow.pub /home/condor_pool/.ssh/workflow.pub
COPY keys/workflow.pub /home/condor_pool/.ssh/authorized_keys

RUN su - condor_pool -c ''
RUN chmod 600 /home/condor_pool/.ssh/workflow
RUN chmod 644 /home/condor_pool/.ssh/workflow.pub
RUN chmod 644 /home/condor_pool/.ssh/authorized_keys
RUN chown -R condor_pool:condor_pool /home/condor_pool/.ssh

COPY supervisord/supervisord.conf /etc/supervisord.conf
COPY supervisord/condor.ini /etc/supervisord.d/condor.ini
COPY supervisord/autofs.ini /etc/supervisord.d/autofs.ini
COPY supervisord/sshd.ini /etc/supervisord.d/sshd.ini

COPY cvmfs/default.local /etc/cvmfs/default.local

COPY condor/condor-wrapper.sh /usr/local/sbin/condor-wrapper.sh
COPY condor/condor_config.local /etc/condor/condor_config.local

COPY run.sh /usr/local/sbin/run.sh

RUN chmod +x /usr/local/sbin/run.sh
RUN chmod +x /usr/local/sbin/condor-wrapper.sh

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/sbin/run.sh"]
