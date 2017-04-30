from __future__ import print_function, division

import json
import numpy as np
import os
import requests
import re

from app.models import Review, Game, Tag
from app.utils import data_file
from app.models.game import iter_all_games
from app.models.review import saved_review_generator
from app.models.tag import compute_reverse_index, create_tag_list
from datetime import datetime

def refresh_games_table():
    games = list(iter_all_games())
    failed = Game.batch_save(games)
    with open(data_file("failed_games.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed), f, default=lambda o: o.__dict__, indent=2)
    return games

def refresh_tags_table(games):
    tag_reverse_index = compute_reverse_index(games)
    tags = create_tag_list(tag_reverse_index)
    failed = Tag.batch_save(tags)
    with open(data_file("failed_tags.json"), "w") as f:
        json.dump(map(lambda g: g.to_json(), failed), f, default=lambda o: o.__dict__, indent=2)
    return tags

def get_missing_reviews(games):
    score_ranks = np.array(map(lambda g: g.score_rank, games))
    order = np.argsort(score_ranks)
    for i in reversed(order):
        app_id = games[i].app_id
        reviews_file = data_file("reviews", "%d.json"%app_id)
        if not os.path.exists(reviews_file):
            print(datetime.now().time(), "Getting reviews for", app_id)
            reviews = Review.get_reviews_from_steam(app_id)
            with open(data_file("reviews", reviews_file), "w") as f:
                json.dump(map(lambda r: r.to_json(), reviews), f, indent=2)
        else:
            print(datetime.now().time(), "Reviews for", app_id, "already exist!")


def refresh_database():
    # games = refresh_games_table()
    # tags = refresh_tags_table(games)
    get_missing_reviews(list(iter_all_games()))

if __name__ == '__main__':
    refresh_database()
