import json

from tornado.web import RequestHandler
from utils import message, error, decode_text
from utils import NO_MONGO_ID, Singleton


class Image:

  def __init__(self, id, cmd=None, args=[], env={}, ports=[], is_privileged=True):
    self.__id = id
    self.__cmd = cmd
    self.__args = args
    self.__env = env
    self.__ports = ports
    self.__is_privileged = is_privileged

  @property
  def id(self):
    return self.__id

  @property
  def args(self):
    return self.__args

  @property
  def cmd(self):
    return self.__cmd

  @property
  def env(self):
    return self.__env

  @property
  def ports(self):
    return self.__ports

  @property
  def is_privileged(self):
    return self.__is_privileged

  def to_dict(self):
    return dict(id=self.id, cmd=self.cmd, args=self.args, env=self.env,
                ports=self.ports, is_privileged=self.is_privileged)


class ImageManager(metaclass=Singleton):

  def __init__(self, db):
    self.__image_col = db.images

  def get_all_images(self):
    return 200, json.dumps(list(self.__image_col.find(projection=NO_MONGO_ID)))

  def get_image(self, id, instance=False):
    image = self.__image_col.find_one(dict(id=id), projection=NO_MONGO_ID)
    if not image:
      return 404, error("Image '%s' is not found"%id)
    return 200, Image(**image) if instance else json.dumps(image)

  def add_image(self, id, cmd=None, args=[], env={}, ports=[], is_privileged=True):
    if self.__image_col.find_one(dict(id=id)):
      return 409, error("Image '%s' already exists"%id)
    image = Image(id, cmd, args, env, ports, is_privileged)
    self.__image_col.insert_one(image.to_dict())
    return 201, json.dumps(image.to_dict())

  def delete_image(self, id):
    res = self.__image_col.delete_one(dict(id=id))
    if res.deleted_count == 0:
      return 404, error("Image '%s' is not found"%id)
    return 200, message("Image '%s' has been deleted"%id)


class ImagesHandler(RequestHandler):

  def initialize(self, db):
    self.__image_mgr = ImageManager(db)

  def get(self):
    status, response = self.__image_mgr.get_all_images()
    self.set_status(status)
    self.write(response)

  def post(self):
    body = decode_text(self.request.body)
    status, response = self.__image_mgr.add_image(**json.loads(body))
    self.set_status(status)
    self.write(response)


class ImageHandler(RequestHandler):

  def initialize(self, db):
    self.__image_mgr = ImageManager(db)

  def get(self, image_id):
    status, response = self.__image_mgr.get_image(image_id)
    self.set_status(status)
    self.write(response)

  def delete(self, image_id):
    status, response  = self.__image_mgr.delete_image(image_id)
    self.set_status(status)
    self.write(response)
