import sys
import json
import logging


NO_MONGO_ID = dict(_id=False)


def config_logger(log_level):
  root = logging.getLogger()
  root.setLevel(log_level)
  ch = logging.StreamHandler(sys.stdout)
  ch.setLevel(log_level)
  root.addHandler(ch)


def message(msg):
  return json.dumps(dict(message=msg))


def error(msg):
  return json.dumps(dict(error=msg))


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
