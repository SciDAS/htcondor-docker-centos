import json
import requests

from tornado.web import RequestHandler

from utils import message, error, NO_MONGO_ID, Singleton


class Cluster:

  def __init__(self, id, url, hosts, type):
    self.__id = id
    self.__url = url
    self.__type = type
    self.__hosts = hosts

  @property
  def id(self):
    return self.__id

  @property
  def url(self):
    return self.__url

  @property
  def type(self):
    return self.__type

  @property
  def hosts(self):
    return dict(self.__hosts)

  def add_host(self, hostname, ip_addr):
    self.__hosts.setdefault(hostname, ip_addr)

  def remove_host(self, hostname):
    self.__hosts.pop(hostname, None)

  def get_app_status(self, id):
    raise NotImplemented

  def create_app(self, app):
    raise NotImplemented

  def delete_app(self, id):
    raise NotImplemented

  def to_dict(self):
    return dict(id=self.id, url=self.url, type=self.type, hosts=self.hosts)


class MarathonCluster(Cluster):

  def __init__(self, id, url, hosts):
    super(MarathonCluster, self).__init__(id, url, hosts, 'marathon')

  def get_app(self, id):
    resp = requests.get('%s/v2/apps/%s'%(self.url, id))
    return resp.status_code, resp.text

  def create_app(self, app):
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
    resp = requests.post('%s/v2/apps'%self.url, data=json.dumps(request))
    return resp.status_code, resp.text

  def delete_app(self, id):
    resp = requests.delete('%s/v2/apps/%s'%(self.url, id))
    return resp.status_code, resp.text


class ClusterManager(metaclass=Singleton):

  def __init__(self, db):
    self.__cluster_col = db.clusters

  def get_all_clusters(self):
    return 200, json.dumps(list(self.__cluster_col.find(projection=NO_MONGO_ID)))

  def get_cluster(self, id, instance=False):
    cluster = self.__cluster_col.find_one(dict(id=id), projection=NO_MONGO_ID)
    if not cluster:
      return 404, error("Cluster '%s' is not found"%id)
    if instance:
      cluster_type = self.get_cluster_type(cluster.pop('type', None))
      return 200, cluster_type(**cluster)
    return 200, json.dumps(cluster)

  def add_cluster(self, id, url, hosts, type):
    if self.__cluster_col.find_one(dict(id=id)):
      return 409, error("Cluster '%s' already exists"%id)
    cluster = None
    if not hosts:
      return 400, error('Host(s) are not specified')
    if type == 'marathon':
      cluster = MarathonCluster(id, url, hosts)
    if not cluster:
      return 400, error('Unknown cluster type: %s'%type)
    self.__cluster_col.insert_one(cluster.to_dict())
    return 201, json.dumps(cluster.to_dict())

  def delete_cluster(self, id):
    res = self.__cluster_col.delete_one(dict(id=id))
    if res.deleted_count == 0:
      return 404, error("Cluster '%s' is not found"%id)
    return 200, message("Cluster '%s'  has been deleted"%id)

  def allocate_cluster(self, resources, data):
    cluster = self.__cluster_col.find_one(projection=NO_MONGO_ID)
    cluster_type = self.get_cluster_type(cluster.pop('type', None))
    return cluster_type(**cluster)

  @staticmethod
  def get_cluster_type(cluster_type):
    if cluster_type == 'marathon':
      return MarathonCluster
    return None

class ClustersHandler(RequestHandler):

  def initialize(self, db):
    self.__cluster_mgr = ClusterManager(db)

  def get(self):
    status, response = self.__cluster_mgr.get_all_clusters()
    self.set_status(status)
    self.write(response)

  def post(self):
    status, response = self.__cluster_mgr.add_cluster(**json.loads(self.request.body))
    self.set_status(status)
    self.write(response)


class ClusterHandler(RequestHandler):

  def initialize(self, db):
    self.__cluster_mgr = ClusterManager(db)

  def get(self, id):
    status, response = self.__cluster_mgr.get_cluster(id)
    self.set_status(status)
    self.write(response)

  def delete(self, id):
    status, response = self.__cluster_mgr.delete_cluster(id)
    self.set_status(status)
    self.write(response)
