import json

from enum import Enum
from tornado.web import RequestHandler

from cluster import ClusterManager
from image import ImageManager
from utils import message, error, NO_MONGO_ID, Singleton


class ApplianceStatus(Enum):

  SUBMITTED = 'submitted'
  STAGING = 'staging'
  RUNNING = 'running'
  FAILED = 'failed'
  UNKNOWN = 'unknown'


class Appliance:

  def __init__(self, id, image, resources, data, cmd=None, args=[], env={},
               status=ApplianceStatus.UNKNOWN, cluster=None, **kwargs):
    self.__id = id
    self.__image = image
    self.__resources = resources
    self.__data = data
    self.__cmd = cmd if cmd else image.cmd
    self.__args = image.args + args if image.args else args
    self.__env = env
    self.__status = status
    self.__cluster = cluster
    self.__access_points = []
    if image and image.env:
      self.__env.update(image.env)

  @property
  def id(self):
    return self.__id

  @property
  def image(self):
    return self.__image

  @property
  def resources(self):
    return self.__resources

  @property
  def data(self):
    return self.__data

  @property
  def cmd(self):
    return self.__cmd

  @property
  def args(self):
    return self.__args

  @property
  def env(self):
    return self.__env

  @property
  def status(self):
    return self.__status

  @status.setter
  def status(self, status):
    self.__status = status

  @property
  def cluster(self):
    return self.__cluster

  @cluster.setter
  def cluster(self, cluster):
    self.__cluster = cluster

  @property
  def access_points(self):
    return list(self.__access_points)

  def add_access_point(self, ap):
    self.__access_points.append(ap)

  def to_dict(self):
    return dict(id=self.id,
                image=self.image.id if self.image else None,
                resources=self.resources,
                status=self.status.value,
                cluster=self.cluster.id if self.cluster else None,
                accessPoints=self.access_points,
                data=self.data,
                args=self.args,
                env=self.env)


class ApplianceManager(metaclass=Singleton):

  def __init__(self, db):
    self.__app_col = db.appliances
    self.__cluster_mgr = ClusterManager(db)
    self.__image_mgr = ImageManager(db)

  def get_all_appliances(self):
    return 200, json.dumps(list(self.__app_col.find(projection=NO_MONGO_ID)))

  def get_appliance(self, id):
    app = self.__app_col.find_one(dict(id=id), projection=NO_MONGO_ID)
    if not app:
      return 404, error("Appliance '%s' is not found"%id)
    if app['cluster']:
      _, app['image'] = self.__image_mgr.get_image(app['image'], True)
      _, app['cluster'] = self.__cluster_mgr.get_cluster(app['cluster'], True)
      app = Appliance(**app)
      status, app_info = app.cluster.get_app(id)
      if status == 200:
        app_info = json.loads(app_info)['app']
        app_ports = app_info['container']['docker']['portMappings']
        tasks = app_info['tasks']
        if tasks:
          task = app_info['tasks'][0]
          host_ports = task['ports']
          host_ip = app.cluster.hosts.get(task['host'], None)
          if len(host_ports) == len(app_ports):
            for i, p in enumerate(app_ports):
              app.add_access_point(
                '%s:%d -> %d'%(host_ip, host_ports[i], p['containerPort']))
          if task['state'] == 'TASK_RUNNING':
            app.status = ApplianceStatus.RUNNING
          elif task['state'] == 'TASK_STAGING':
            app.status = ApplianceStatus.STAGING
          elif task['state'] == 'TASK_FAILED':
            app.status = ApplianceStatus.FAILED
          else:
            print(task['state'])
            app.status = ApplianceStatus.UNKNOWN
    return 200, json.dumps(app.to_dict())

  def create_appliance(self, id, image, resources, data, cmd=None, args=[], env={}):
    if self.__app_col.find_one(dict(id=id)):
      return 409, error("Appliance '%s' already exists"%id)
    image_id = image
    status, image = self.__image_mgr.get_image(image_id, True)
    if status == 404:
      return status, error("Image '%s' is not found"%image_id)
    app = Appliance(id, image, resources, data, cmd, args, env)
    cluster = self.__cluster_mgr.allocate_cluster(app.resources, app.data)
    status, resp = cluster.create_app(app)
    if status == 201:
      app.status = ApplianceStatus.SUBMITTED
      app.cluster = cluster
      self.__app_col.insert_one(app.to_dict())
      return status, json.dumps(app.to_dict())
    elif status == 409:
      return 409, error("Appliance '%s' already exists"%id)
    return status, resp

  def delete_appliance(self, id):
    app = self.__app_col.find_one(dict(id=id))
    if not app:
      return 404, error("Appliance '%s' is not found"%id)
    if app['cluster']:
      status, cluster = self.__cluster_mgr.get_cluster(app['cluster'], True)
      if status == 200:
        status, resp = cluster.delete_app(id)
    self.__app_col.delete_one(dict(id=id))
    return 200, message("Appliance '%s' has been deleted"%id)


class AppliancesHandler(RequestHandler):

  def initialize(self, db):
    self.__app_mgr = ApplianceManager(db)

  def get(self):
    status, response = self.__app_mgr.get_all_appliances()
    self.set_status(status)
    self.write(response)

  def post(self):
    status, response = self.__app_mgr.create_appliance(**json.loads(self.request.body))
    self.set_status(status)
    self.write(response)


class ApplianceHandler(RequestHandler):

  def initialize(self, db):
    self.__app_mgr = ApplianceManager(db)

  def get(self, id):
    status, response = self.__app_mgr.get_appliance(id)
    self.set_status(status)
    self.write(response)

  def delete(self, id):
    status, response = self.__app_mgr.delete_appliance(id)
    self.set_status(status)
    self.write(response)
