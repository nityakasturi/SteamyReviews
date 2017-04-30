from app.dynamodb.utils import create_dynamo_table
from app.models.review import Review
from app.models.game import Game
from app.models.tag import Tag
from app.models import refresh as refresh

def initialize():
    create_dynamo_table(Review)
    create_dynamo_table(Tag)
    create_dynamo_table(Game)

    Game._load_caches()
