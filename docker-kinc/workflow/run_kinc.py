#!/usr/bin/env python3

import re
import subprocess

from subprocess import Popen, PIPE

def get_submitter_container_id():
  out, err = Popen('docker ps'.split(), stdout=PIPE, stderr=PIPE).communicate()
  for l in out.decode('ascii').split('\n'):
    if 'submitter' in l:
        return re.split(r'[ \t]', l)[0].strip()


def submit_workflow(container_id, n_jobs):
  print('Submit KINC workflow ...', )
  out, err = Popen('docker exec -u condor_pool -e USER=condor_pool %s /bin/bash -c "source /etc/profile; cd /home/condor_pool/OSG-KINC/; ./submit %d"'%(container_id, n_jobs),
                 stdout=PIPE, stderr=PIPE, shell=True).communicate()
  print('Success')
  for l in out.decode('ascii').split('\n'):
      if 'pegasus-status' in l:
          return '/usr/bin/%s'%l.split(':')[-1].strip()


def monitor_workflow(container_id, check_status_cmd):
  subprocess.call('watch docker exec -it -u condor_pool %s %s'%(container_id, check_status_cmd), shell=True)


if __name__ == '__main__':
  container_id = get_submitter_container_id()
  check_status_cmd = submit_workflow(container_id, 100)
  monitor_workflow(container_id, check_status_cmd)
