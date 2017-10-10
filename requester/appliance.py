import json
import uuid
import requests

from enum import Enum
from tornado.web import RequestHandler

from image import ImageManager
from cluster import get_cluster_type
from utils import message, error, decode_text
from utils import NO_MONGO_ID, Singleton, MESOS_COORDINATOR_URL, APPLICATION_JSON


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
    self.__args = image.args if image.args else args
    self.__env = env
    self.__cluster = cluster
    self.__access_points = []
    self.status = status
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
    if status == 'TASK_RUNNING' or status == 'running':
      self.__status = ApplianceStatus.RUNNING
    elif status == 'TASK_STAGING' or status == 'staging':
      self.__status = ApplianceStatus.STAGING
    elif status == 'TASK_FAILED' or status == 'failed':
      self.__status = ApplianceStatus.FAILED
    else:
      self.__status = ApplianceStatus.UNKNOWN

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
                cluster=self.cluster.to_dict() if self.cluster else None,
                accessPoints=self.access_points,
                data=self.data,
                args=self.args,
                env=self.env)


class ApplianceManager(metaclass=Singleton):

  def __init__(self, db):
    self.__app_col = db.appliances
    self.__image_mgr = ImageManager(db)

  def get_all_appliances(self):
    return 200, json.dumps(list(self.__app_col.find(projection=NO_MONGO_ID)))

  def get_appliance(self, id):
    app = self.__app_col.find_one(dict(id=id), projection=NO_MONGO_ID)
    if not app:
      return 404, error("Appliance '%s' is not found"%id)
    _, app['image'] = self.__image_mgr.get_image(app['image'], True)
    if app['cluster']:
      cluster_type = get_cluster_type(app['cluster'].pop('type', None))
      app['cluster'] = cluster_type(**app['cluster'])
    app = Appliance(**app)
    if app.cluster:
      status, app_info = app.cluster.get_app(id)
      if status == 200:
        app_info = json.loads(app_info)['app']
        app_ports = app_info['container']['portMappings']
        tasks = app_info['tasks']
        if tasks:
          task = app_info['tasks'][0]
          host_ports = task['ports']
          host_ip = task.get('host', None)
          if len(host_ports) == len(app_ports):
            for i, p in enumerate(app_ports):
              app.add_access_point(
                '%s:%d -> %d'%(host_ip, host_ports[i], p['containerPort']))
          app.status = task['state']
    return 200, json.dumps(app.to_dict())

  def create_appliance(self, id, image, resources, data, callback,
                       cmd=None, args=[], env={}):

    def submit_offer_request(app):
      offer_req = dict(
        requesterAddress='%s/%s/offer'%(callback, id),
        coordinatorAddress=MESOS_COORDINATOR_URL,
        name=id,
        resources='cpus:%.1f;mem:%.1f'%(app.resources['cpus'], app.resources['mem']),
        dockerImage=app.image.id,
        globalFrameworkId=uuid.uuid4().hex
      )
      r = requests.post(MESOS_COORDINATOR_URL, headers=APPLICATION_JSON,
                        data=json.dumps(offer_req))
      return r.status_code, r.text

    if self.__app_col.find_one(dict(id=id)):
      return 409, error("Appliance '%s' already exists"%id)
    image_id = image
    status, image = self.__image_mgr.get_image(image_id, True)
    if status == 404:
      return status, error("Image '%s' is not found"%image_id)
    app = Appliance(id, image, resources, data, cmd, args, env,
                    status=ApplianceStatus.SUBMITTED)
    self.__app_col.insert_one(app.to_dict())
    status, resp = submit_offer_request(app)
    if status != 200:
      self.__app_col.delete_one(dict(id=app.id))
      return status, resp
    return 201, json.dumps(app.to_dict())

  def accept_offer(self, id, offers):
    app = self.__app_col.find_one(dict(id=id), projection=NO_MONGO_ID)
    if not app:
      return 404, error("Appliance '%s' is not found"%id)
    _, app['image'] = self.__image_mgr.get_image(app['image'], True)
    app = Appliance(**app)
    offer = offers[-1]
    print(offer)
    cluster_type = get_cluster_type('marathon')
    cluster = cluster_type('http://%s'%offer['Marathon'])
    status, resp = cluster.create_app(app, agent=offer['agent'])
    if status == 201:
      self.__app_col.update_one(dict(id=app.id),
                                {'$set': dict(cluster=cluster.to_dict())})
      return status, json.dumps(app.to_dict())
    elif status == 409:
      return 409, error("Appliance '%s' already exists"%id)
    return status, resp

  def delete_appliance(self, id):
    app = self.__app_col.find_one(dict(id=id))
    if not app:
      return 404, error("Appliance '%s' is not found"%id)
    if app['cluster']:
      cluster_type = get_cluster_type(app['cluster'].pop('type', None))
      cluster = cluster_type(**app['cluster'])
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
    body = decode_text(self.request.body)
    callback = 'http://%s%s'%(self.request.host, self.request.uri)
    status, response = self.__app_mgr.create_appliance(callback=callback,
                                                       **json.loads(body))
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


class OfferHandler(RequestHandler):

  def initialize(self, db):
    self.__app_mgr = ApplianceManager(db)

  def post(self, id):
    offers = json.loads(decode_text(self.request.body))
    status, resp = self.__app_mgr.accept_offer(id, [offers[k] for k in sorted(offers)
                                                    if isinstance(offers[k], dict)])
    self.set_status(status)
    self.write(resp)



