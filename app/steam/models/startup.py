from __future__ import print_function, division

import json
import os
import requests
import re

from . import Review, Game, Tag
from app.steam.util import data_file
from app.steam.models.game import iter_all_games
from app.steam.models.review import saved_review_generator
from app.steam.models.tag import get_tags

def prime_games_table():
    games = list(iter_all_games())
    failed = Game.batch_save(games)
    with open(data_file("failed_games.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed), f, default=lambda o: o.__dict__, indent=2)

def prime_reviews_table():
    Review.batch_save(saved_review_generator())

def prime_tags_table():
    Tag.batch_save(get_tags())

def prime_database():
    prime_games_table()
    prime_reviews_table()
    prime_tags_table()

if __name__ == '__main__':
    prime_database()

