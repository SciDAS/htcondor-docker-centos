import json
import requests


class Cluster:

  def __init__(self, url, type):
    self.__url = url
    self.__type = type

  @property
  def url(self):
    return self.__url

  @property
  def type(self):
    return self.__type

  def get_app(self, app):
    raise NotImplemented

  def create_app(self, app):
    raise NotImplemented

  def delete_app(self, id):
    raise NotImplemented

  def to_dict(self):
    return dict(url=self.url, type=self.type)


class MarathonCluster(Cluster):

  def __init__(self, url):
    super(MarathonCluster, self).__init__(url, 'marathon')

  def get_app(self, id):
    resp = requests.get('%s/v2/apps/%s'%(self.url, id))
    return resp.status_code, resp.text

  def create_app(self, app, agent=None):
    '''

    :param app:
    :param agent: IP address of a Mesos agent
    :return:
    '''
    portMappings=[dict(containerPort=p['app_port'],
                       protocol=p.get('protocol', 'tcp'),
                       hostPort=p.get('host_port', 0))
                  for p in app.image.ports if 'app_port' in p]
    request = dict(id=app.id,
                   cpus=app.resources['cpus'],
                   mem=app.resources['mem'],
                   cmd=app.cmd if app.cmd else '',
                   disk=app.resources['disk'],
                   container=dict(type='DOCKER',
                                  docker=dict(image=app.image.id,
                                              network='BRIDGE',
                                              portMappings=portMappings,
                                              privileged=app.image.is_privileged)),
                   args=app.args, env=app.env)
    if agent:
      request['constraints'] = [['hostname', 'CLUSTER', agent]]
    resp = requests.post('%s/v2/apps'%self.url, data=json.dumps(request))
    return resp.status_code, resp.text

  def delete_app(self, id):
    resp = requests.delete('%s/v2/apps/%s'%(self.url, id))
    return resp.status_code, resp.text


def get_cluster_type(cluster_type):
  if cluster_type == 'marathon':
    return MarathonCluster
  return None
