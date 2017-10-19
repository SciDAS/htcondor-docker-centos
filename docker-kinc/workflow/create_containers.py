#!/usr/bin/env python3

import sys
import json
import time
import requests

from argparse import ArgumentParser
from collections import namedtuple

Cluster = namedtuple('Cluster', 'id marathon_uri')
Container = namedtuple('Container', 'id cluster ports image n_cpus mem disk args')

FIELD_MISSING_ERR = '[Error] Field "%s" is missing'


def parse_args():
  parser = ArgumentParser(description='Run containers on distributed Mesos clusters')
  parser.add_argument('-c', '--config', dest='config', default='./config.json', type=str,
                      help='path to JSON configuration file')
  return parser.parse_args()


def parse_config(cfg_file):
  try:
    cfg = json.load(open(cfg_file))
    if 'clusters' not in cfg:
      print(FIELD_MISSING_ERR%'clusters')
      sys.exit(1)
    elif 'containers' not in cfg:
      print(FIELD_MISSING_ERR%'containers')
      sys.exit(1)
    clusters = {cl['id']: Cluster(**cl) for cl in cfg['clusters']}
    containers = {co['id']: Container(**co) for co in cfg['containers']}
    network = cfg['network']
    network['containers'] = {n['id']: n['ip_addr'] for n in network['containers']}
    return clusters, containers, network
  except json.decoder.JSONDecodeError as e:
    print('[Error] Cannot parse config file: %s'%cfg_file)
    sys.exit(2)


def cleanup_containers(containers, clusters):
  for co in containers.values():
    if co.cluster not in clusters:
      continue
    cl = clusters[co.cluster]
    print('Remove container on %s ... '%co.id,)
    resp = requests.delete('%s/%s'%(cl.marathon_uri, co.id))
    print('Success' if resp.ok or resp.status_code == 404 else 'Failed')
  print('Sleep 10 seconds ...')
  time.sleep(10)


def create_containers(containers, clusters, network):
  for co in containers.values():
    if co.cluster not in clusters:
      continue
    cl = clusters[co.cluster]
    print('Create container on %s'%cl.id,)
    print('n_cpus: %.1f, mem: %.1f, disk: %.1f'%(co.n_cpus, co.mem, co.disk))
    container_req = {
      'id': co.id,
      'cpus': co.n_cpus,
      'mem': co.mem,
      'disk': co.disk,
      'container': {
        'type': 'DOCKER',
        'docker': {
          'image': co.image,
          'network': 'BRIDGE',
          'privileged': True,
        },
        'portMappings': [dict(containerPort=p['container_port'],
                              hostPort=p['host_port'],
                              protocol=p['protocol'])
                         for p in co.ports]
      },
      'args': co.args,
      'env': {
        'WEAVE_CIDR': '%s/16'%network['containers'][co.id],
        'APP_NUM_CORES': str(co.n_cpus),
        'APP_NETWORK': network['cidr']
      }
    }
    resp = requests.post(cl.marathon_uri, data=json.dumps(container_req))
    print('Success' if resp.ok else 'Failed')
    print('Sleep 10 seconds')
  time.sleep(10)

if __name__ == '__main__':
  args = parse_args()
  clusters, containers, network = parse_config(args.config)
  cleanup_containers(containers, clusters)
  create_containers(containers, clusters, network)

