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
from datetime import datetime
from random import sample

def get_missing_reviews_s3(games):
    remaining = set(g.app_id for g in games)
    while len(remaining) > 0:
        app_id, = sample(remaining, 1)
        if not Review.exists_in_s3(app_id):
            print(datetime.now().time(), "Getting reviews for", app_id)
            reviews = Review.get_reviews_from_steam(app_id, 1000)
            Review.upload_to_s3(app_id, reviews)
        else:
            print(datetime.now().time(), "Reviews for", app_id, "already exist!")
            remaining.remove(app_id)

if __name__ == '__main__':
    get_missing_reviews_s3(list(iter_all_games()))
