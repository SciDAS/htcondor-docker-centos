import logging
import tornado

from tornado.web import Application
from pymongo import MongoClient

from image import ImageHandler, ImagesHandler
from cluster import ClusterHandler, ClustersHandler
from appliance import ApplianceHandler, AppliancesHandler
from utils import config_logger


if __name__ == '__main__':
  config_logger(logging.DEBUG)
  db = MongoClient().requester
  Application([
    (r'/appliance', AppliancesHandler, dict(db=db)),
    (r'/appliance/([a-z\/0-9-]+)', ApplianceHandler, dict(db=db)),
    (r'/cluster', ClustersHandler, dict(db=db)),
    (r'/cluster/([a-z\/0-9-]+)', ClusterHandler, dict(db=db)),
    (r'/image', ImagesHandler, dict(db=db)),
    (r'/image/([a-z0-9\/-]+)', ImageHandler, dict(db=db)),
  ]).listen(8080)
  tornado.ioloop.IOLoop.instance().start()
