import logging
import tornado

from tornado.web import Application
from pymongo import MongoClient

from image import ImageHandler, ImagesHandler
from appliance import ApplianceHandler, AppliancesHandler, OfferHandler
from utils import config_logger


if __name__ == '__main__':
  config_logger(logging.DEBUG)
  db = MongoClient(connect=False).requester
  app = Application([
    (r'/appliance', AppliancesHandler, dict(db=db)),
    (r'/appliance/([a-z\/0-9-]+)/offer', OfferHandler, dict(db=db)),
    (r'/appliance/([a-z\/0-9-]+)', ApplianceHandler, dict(db=db)),
    (r'/image', ImagesHandler, dict(db=db)),
    (r'/image/([a-z0-9\/-]+)', ImageHandler, dict(db=db)),

  ])
  server = tornado.httpserver.HTTPServer(app)
  server.bind(9090)
  server.start(0)
  tornado.ioloop.IOLoop.instance().start()
