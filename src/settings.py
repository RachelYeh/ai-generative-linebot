from flask import Flask
app = Flask(__name__)

import logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)-8s] %(message)s', datefmt='%Y%m%d %H:%M:%S')

STATIC_ROOT = "../static/"
HOSTNAME = "127.0.0.1"

import pymongo
client = pymongo.MongoClient("mongodb://.../linebot")
logging.debug(client.list_database_names())
db = client['linebot']
