from __future__ import print_function, division

import json
import os
import requests
import re

from app.steam.models import Review, Game, Tag
from app.steam.util import data_file
from app.steam.models.game import iter_all_games
from app.steam.models.review import saved_review_generator
from app.steam.models.tag import compute_reverse_index, create_tag_list

def refresh_games_table():
    games = list(iter_all_games())
    failed = Game.batch_save(games)
    with open(data_file("failed_games.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed), f, default=lambda o: o.__dict__, indent=2)
    return games

def refresh_tags_table(games):
    tag_reverse_index = compute_reverse_index(games)
    tags = create_tag_list(tag_reverse_index)
    Tag.batch_save(tags)

def refresh_reviews_table():
    Review.batch_save(saved_review_generator())

def refresh_database():
    games = refresh_games_table()
    refresh_tags_table(games)
    # refresh_reviews_table()

if __name__ == '__main__':
    Game.table.delete()
    Tag.table.delete()
    Game.create_table()
    Tag.create_table()
    games = list(iter_all_games())
    failed_games = Game.batch_save(games)
    with open(data_file("failed_games.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed_games), f, default=lambda o: o.__dict__, indent=2)
    tag_reverse_index = compute_reverse_index(games)
    tags = create_tag_list(tag_reverse_index)
    failed_tags = Tag.batch_save(tags)
    with open(data_file("failed_tags.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed_tags), f, default=lambda o: o.__dict__, indent=2)
