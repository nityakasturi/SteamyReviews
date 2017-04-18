import os
basedir = os.path.abspath(os.path.dirname(__file__))

# Different environments for the app to run in

class Config(object):
    DEBUG = False
    CSRF_ENABLED = True
    CSRF_SESSION_KEY = "secret"
    SECRET_KEY = "not_this"
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    DYNAMO_REGION = os.environ.get("DYNAMO_REGION", "us-west-2")
    DYNAMO_DATABASE_URI = os.environ.get("DYNAMO_URL", "http://localhost:8000")

class ProductionConfig(Config):
    DEBUG = False
    DYNAMO_DATABASE_URI = os.environ.get("DYNAMO_URL", "https://dynamodb.us-west-2.amazonaws.com")

class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True

class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
