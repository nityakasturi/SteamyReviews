import nltk
import os

from flask_script import Manager
from app import app
from app.dynamodb.utils import create_dynamo_table
from app.models.review import Review
from app.models.game import Game
from app.models.tag import Tag

manager = Manager(app)

@manager.command
def create_tables():
    create_dynamo_table(Review)
    create_dynamo_table(Tag)
    create_dynamo_table(Game)

@manager.command
def get_punkt():
    nltk.download("punkt")

if __name__ == "__main__":
    manager.run()
