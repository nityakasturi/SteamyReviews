# Gevent needed for sockets
from gevent import monkey
monkey.patch_all()

# Imports
import os
from flask import Flask, render_template
from flask_socketio import SocketIO
import boto3

# Configure app
socketio = SocketIO()
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])

import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download("punkt")

# DB
db = boto3.resource("dynamodb",
                    region_name=app.config["DYNAMO_REGION"],
                    endpoint_url=app.config["DYNAMO_DATABASE_URI"])
s3 = boto3.resource("s3", region_name=app.config["DYNAMO_REGION"])


from app import models
models.initialize()

# Initialize the controllers
from app import controllers

# Initialize app w/SocketIO
socketio.init_app(app)

# HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404
