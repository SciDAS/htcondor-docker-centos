#!/usr/bin/env python3

import os
import sys
import yaml
import json
import shutil
import subprocess
from argparse import ArgumentParser


SSH_CMD = '/usr/bin/ssh ' \
          '-oConnectTimeout=10 ' \
          '-oStrictHostKeyChecking=no ' \
          '-oUserKnownHostsFile=/dev/null ' \
          '-oBatchMode=yes ' \
          '-oPasswordAuthentication=no ' \
          '-p22 ' \
          '-i %s -tt ' \
          '%s@%s "%s"'
SCP_CMD = '/usr/bin/scp -r ' \
          '-oConnectTimeout=10 ' \
          '-oStrictHostKeyChecking=no ' \
          '-oUserKnownHostsFile=/dev/null ' \
          '-oBatchMode=yes ' \
          '-oPasswordAuthentication=no ' \
          '-p22 ' \
          '-i %s ' \
          '%s %s@%s:%s'


def ssh(login, key, dest, cmds):
  cmd = SSH_CMD%(key, login, dest['public'], '\n'.join(cmds))
  print(cmd)
  subprocess.call(cmd, shell=True)


def scp(login, key, dest, files, path):
  subprocess.call(SCP_CMD%(key, ' '.join(files), login, dest['public'], path), shell=True)


def get_args():
  parser = ArgumentParser(description='Deploy DC/OS on a cluster running CentOS 7')
  parser.add_argument('-k', '--key-file', dest='ssh_key', required=True, type=str,
                      help='SSH private key for accessing nodes')
  parser.add_argument('-c', '--config', dest='cfg', required=True, type=str,
                      help='JSON deployment configuration file')
  return parser.parse_args()


def parse_config(cfg):
  try:
    cfg = json.load(open(cfg))
    return cfg['login'], cfg['bootstrap'], cfg['masters'], cfg['agents']
  except Exception as e:
    raise e
    sys.exit(1)

def create_tmp_dir():
  if not os.path.exists('tmp'):
    os.mkdir('tmp')

def install_common_packages(login, key, nodes):
  for n in nodes:
    ssh(login, key, n, ['sudo yum install -y wget vim bind-utils ntp'])


def install_docker(login, key, nodes):
  with open('tmp/docker.repo', 'w') as f:
    f.writelines('''[dockerrepo]
name=Docker Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/$releasever/
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
    ''')
  with open('tmp/override.conf', 'w') as f:
    f.writelines('''[Service]
ExecStart=
ExecStart=/usr/bin/docker daemon --storage-driver=overlay -H fd://
    ''')
  for n in nodes:
    scp(login, key, n, ['tmp/docker.repo', 'tmp/override.conf'], '~')
    ssh(login, key, n, ['echo overlay | sudo tee -a /etc/modules-load.d/overlay.conf',
                        'sudo modprobe overlay',
                        'sudo mv ~/docker.repo /etc/yum.repos.d',
                        'sudo mkdir -p /etc/systemd/system/docker.service.d',
                        'sudo mv ~/override.conf /etc/systemd/system/docker.service.d',
                        'sudo yum install -y --tolerant docker-engine-1.11.0',
                        'sudo systemctl start docker',
                        'sudo usermod -aG docker %s'%login
                        ])


def install_prereqs(login, key, masters, agents):
  for n in masters + agents:
    ssh(login, key, n, ['sudo yum install -y tar xz unzip curl ipset',
                        'sudo groupadd nogroup'])


def prepare_bootstrap_node(login, key, node, masters, agents):
  generate_config_yaml('dcos-test', login, masters, agents)

  with open('tmp/ip-detect', 'w') as f:
    f.writelines(r'''#!/usr/bin/env bash
set -o nounset -o errexit
export PATH=/usr/sbin:/usr/bin:$PATH
echo $(ip addr show eno1 | grep -Eo '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)''')

  scp(login, key, node, [key, 'tmp/config.yaml', 'tmp/ip-detect'], '~')
  ssh(login, key, node, ['curl -P ~ -O https://downloads.dcos.io/dcos/EarlyAccess/commit/14509fe1e7899f439527fb39867194c7a425c771/dcos_generate_config.sh',
                         'mkdir -p ~/genconf',
                         'mv ~/id_rsa ~/genconf/ssh_key',
                         'mv ~/config.yaml ~/genconf',
                         'mv ~/ip-detect ~/genconf',
                         'sudo bash ~/dcos_generate_config.sh --genconf',
                         'sudo bash ~/dcos_generate_config.sh --deploy',
                         'sudo bash ~/dcos_generate_config.sh --postflight'])


def generate_config_yaml(cl_name, login, masters, agents):
  with open('tmp/config.yaml', 'w') as f:
    yaml.dump({
      'ssh_port': 22,
      'ssh_user': login,
      'cluster_name': cl_name,
      'master_discovery': 'static',
      'agent_list': [a['private'] for a in agents],
      'master_list': [m['private'] for m in masters]
    }, f, default_flow_style=False)


def cleanup():
  shutil.rmtree('tmp')


if __name__ == '__main__':
  args = get_args()
  ssh_key = args.ssh_key
  login, bootstrap, masters, agents = parse_config(args.cfg)
  create_tmp_dir()
  install_common_packages(login, ssh_key, masters + agents + [bootstrap])
  install_docker(login, ssh_key, masters + agents + [bootstrap])
  install_prereqs(login, ssh_key, masters, agents)
  prepare_bootstrap_node(login, ssh_key, bootstrap, masters, agents)
  cleanup()
