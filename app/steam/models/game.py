from __future__ import print_function, division

import json
import logging
import os
import requests
import re
import sys
import time

from . import Review
from app import app
from app.dynamodb import dynamodb, utils
from app.steam.util import data_file
from bs4 import BeautifulSoup
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from cachetools import LRUCache, Cache
from decimal import Decimal
from datetime import datetime
from functools import partial
from itertools import islice
from Levenshtein import distance

reviews_re = re.compile(r"\(([0-9,]+) reviews?\)")
userscore_to_digit = {
    "Overwhelmingly Positive": 8,
    "Very Positive": 7,
    "Positive": 6,
    "Mostly Positive": 5,
    "Mixed": 4,
    "Mostly Negative": 3,
    "Negative": 2,
    "Very Negative": 1,
    "Overwhelmingly Negative": 0
}
digit_to_userscore = {score: r for r,score in userscore_to_digit.iteritems()}

class GameNotFoundException(Exception):
    def __init__(self, app_id):
        super(GameNotFoundException, self).__init__("Game %s does not exist!"%app_id)

# This has to be out here because it can"t be a classmethod but it also can"t be __private
def _get_no_cache(app_id):
    res = Game.table.query(KeyConditionExpression=Key(Game.hash_key[0]).eq(app_id))
    if len(res["Items"]) > 0:
        game = Game.from_dynamo_json(res["Items"][0])
    else:
        # if we couldn"t find it in Dynamo, try to get it from Steamspy
        game = Game.get_from_steamspy(app_id)
    if (app.config["UPDATE_GAME_ON_GET"]
        and (game.userscore is None or (datetime.utcnow() - game.last_updated).days >= 7)):
        game.update_and_save()
    return game

class Game(object):
    table_name = "apps"
    table = dynamodb.Table(table_name)
    hash_key = ("app_id", utils.NUMBER)
    sorting_key = None
    _game_cache = LRUCache(maxsize=app.config["GAME_CACHE_SIZE"], missing=_get_no_cache)
    _name_inverted_index = {}

    @classmethod
    def create_table(cls):
        utils.create_dynamo_table(cls)
        # If in production, just pull everything down and fill the cache completely
        if app.config["GAME_CACHE_PULL_ON_LOAD"]:
            # We"re still going to use the Cache class here instead of a dict because it"s slightly
            # better at handling missing values than a defaultdict
            cls._game_cache = Cache(sys.maxint, missing=_get_no_cache)
            for game in iter_all_games():
                if len(game.tags) > 0:
                    cls._game_cache[int(game.app_id)] = game
                    cls._name_inverted_index[game.normalized_name] = int(game.app_id)
            logging.info("Loaded game cache")
        else:
            cls._name_inverted_index = cls.get_name_inverted_index()
            logging.info("Loaded name inverted index")

    @classmethod
    def get_from_steamspy(cls, app_id):
        res = requests.get("http://steamspy.com/api.php?request=appdetails&appid=%s"%app_id)
        if not 200 <= res.status_code < 300:
            raise GameNotFoundException(app_id)
        else:
            return cls.from_steampspy_json(res.json())

    @classmethod
    def from_steampspy_json(cls, game):
        # We don"t use any of these guys so we have to delete them
        game.pop("owners_variance", None)
        game.pop("players_forever", None)
        game.pop("players_forever_variance", None)
        game.pop("players_2weeks", None)
        game.pop("players_2weeks_variance", None)
        game.pop("average_forever", None)
        game.pop("average_2weeks", None)
        game.pop("median_forever", None)
        game.pop("median_2weeks", None)
        game.pop("ccu", None)

        game["app_id"] = int(game.pop("appid"))
        game["price"] = float(game["price"] or 0) / 100 # price is in cents

        game["developer"] = game.get("developer", "") or ""
        game["publisher"] = game.get("publisher", "") or ""

        if len(game["tags"]) > 0 and isinstance(game["tags"], dict):
            tags = {k.lower().strip(): v for k, v in game["tags"].iteritems()}
        else:
            tags = dict()
        game["tags"] = tags

        # we have to set the actual userscore and num_reviews to -1 because this API doesn"t return
        # those values
        game["userscore"] = None
        game["num_reviews"] = None

        if game["score_rank"] == "":
            game["score_rank"] = None
        else:
            game["score_rank"] = game["score_rank"]

        game["last_updated"] = datetime.utcnow()
        return cls(**game)

    @classmethod
    def from_json(cls, game_json):
        game_json["last_updated"] = datetime.utcfromtimestamp(int(game_json["last_updated"]))
        return cls(**game_json)

    @classmethod
    def from_dynamo_json(cls, dynamo_json):
        dynamo_json["name"] = dynamo_json.get("name") or ""
        dynamo_json["normalized_name"] = dynamo_json.get("normalized_name") or ""
        dynamo_json["developer"] = dynamo_json.get("developer") or ""
        dynamo_json["publisher"] = dynamo_json.get("publisher") or ""
        dynamo_json["price"] = float(dynamo_json["price"])
        if dynamo_json["tags"] is not None and len(dynamo_json["tags"]) > 0:
            dynamo_json["tags"] = {k: int(v) for k, v in dynamo_json["tags"].iteritems()}
        else:
            dynamo_json["tags"] = dict()
        dynamo_json["last_updated"] = int(dynamo_json["last_updated"])
        return cls.from_json(dynamo_json)

    @classmethod
    def batch_save(cls, games):
        return utils.batch_save(cls, games)

    @classmethod
    def find_by_name(cls, name):
        name = normalize(name)
        name_filter = Attr("normalized_name").eq(normalize(name))
        for game in cls._game_cache.values():
            if game.normalized_name == name:
                return [game]
        # return map(cls.from_dynamo_json, utils.table_scan(cls, FilterExpression=name_filter))

    @classmethod
    def correct_game_name(cls, game_name):
        game_name = normalize(game_name)
        best_match = min(cls._name_inverted_index.keys(), key=partial(distance, game_name))
        return cls.get(cls._name_inverted_index[best_match])

    @classmethod
    def get(cls, to_get):
        if isinstance(to_get, int):
            return cls._game_cache[to_get]
        elif not (isinstance(to_get, set) and len(to_get) > 0):
            raise ValueError("`to_get` must be a non-empty set! (got %s)"%type(to_get))
        else:
            results = dict()
            for app_id in to_get:
                # this is a little funky, but it just standardizes how we get a single game, since
                # we can"t really to actual multi-gets from Dynamo
                results[app_id] = cls.get(app_id)
            return results

    @classmethod
    def get_all(cls):
        return map(cls.from_dynamo_json, utils.table_scan(cls))

    @classmethod
    def get_unscored(cls, limit=1000):
        attr_cond = Attr("userscore").eq(None)
        return map(cls.from_dynamo_json,
                   islice(utils.table_scan(cls, FilterExpression=attr_cond, Limit=limit), limit))

    @classmethod
    def get_name_inverted_index(cls):
        res = utils.table_scan(cls, ProjectionExpression="normalized_name, app_id")
        index = dict()
        for item in res:
            index[item["normalized_name"].encode("ascii")] = int(item["app_id"])
        return index

    def __init__(self, app_id, name, developer, publisher, owners, userscore, num_reviews,
                 score_rank, price, tags, last_updated,  **kwargs):
        self.app_id = app_id
        self.name = name
        # this one is in the kwargs because it"s optional but depends on self.name
        self.normalized_name = kwargs.get("normalized_name") or normalize(self.name)
        self.normalized_name = self.normalized_name.encode("ascii")
        self.developer = developer
        self.publisher = publisher
        self.owners = owners
        self.userscore = userscore
        self.num_reviews = num_reviews
        self.score_rank = score_rank
        self.price = price
        self.tags = tags
        self.last_updated = last_updated

    def __repr__(self):
        return "Game(app_id=%d,name=%s)"%(self.app_id, self.normalized_name)

    def __str__(self):
        return self.__repr__()

    def steam_url(self):
        return "http://store.steampowered.com/app/%s"%self.app_id

    def steam_image_url(self):
        return "http://cdn.akamai.steamstatic.com/steam/apps/%s/header.jpg"%self.app_id

    def to_json(self):
        return {
            "app_id": self.app_id,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "developer": self.developer,
            "publisher": self.publisher,
            "owners": self.owners,
            "userscore": self.userscore,
            "num_reviews": self.num_reviews,
            "score_rank": self.score_rank,
            "price": self.price,
            "tags": self.tags if len(self.tags) > 0 else None,
            "last_updated": int(time.mktime(self.last_updated.timetuple())),
        }

    def to_dynamo_json(self):
        dynamo_json = self.to_json()
        dynamo_json["price"] = Decimal(str(self.price))
        dynamo_json["name"] = self.name or None
        dynamo_json["normalized_name"] = self.normalized_name or None
        dynamo_json["developer"] = self.developer or None
        dynamo_json["publisher"] = self.publisher or None
        return dynamo_json

    def save(self):
        Game.table.put_item(Item=self.to_dynamo_json())

    def fetch_more_reviews(self):
        Review.batch_save(Review.fetch_new_reviews(self.app_id))

    def get_saved_reviews(self, key_condition, filter_expression, max_items):
        primary_condition = Key(Review.hash_key).eq(self.app_id)
        if key_condition is not None:
            primary_condition = primary_condition & key_condition
        return Review.get(primary_condition, filter_expression, max_items)

    def get_recent_reviews(self, max_reviews=100):
        return self.get_saved_reviews(None, None, max_reviews)

    def update_and_save(self):
        self.update_steamspy_attributes()
        self.update_userscore()
        self.last_updated = datetime.utcnow()
        self.save()

    def update_steamspy_attributes(self):
        new_game = Game.get_from_steamspy(self.app_id)
        self.name = new_game.name
        self.developer = new_game.developer
        self.publisher = new_game.publisher
        self.owners = new_game.owners
        self.userscore = new_game.userscore
        self.num_reviews = new_game.num_reviews
        self.score_rank = new_game.score_rank
        self.price = new_game.price
        self.tags = new_game.tags

    def update_userscore(self):
        page = requests.get("http://store.steampowered.com/app/%s"%self.app_id)
        soup = BeautifulSoup(page.text, "lxml")

        summary_section = soup.find_all("div", class_="summary_section")
        for sec in summary_section:
            title, score, num_reviews = sec.stripped_strings
            if "overall" in title.lower():
                matches = reviews_re.match(num_reviews)
                if score in userscore_to_digit and matches is not None:
                    self.userscore = userscore_to_digit[score]
                    num_reviews, = matches.groups()
                    self.num_reviews = int(num_reviews.replace(",", ""))
                    print("Succesfully updated userscore for", self.app_id)
                    return

        # This is just so that we don"t retry any games that can"t be scored (maybe because they
        # haven"t come out yet) automatically.
        print("Could not update userscore for", self.app_id)
        self.userscore = -2
        self.num_reviews = -2

STEAMSPY_JSON = data_file("steamspy_games.json")
def iter_all_games():
    if os.path.exists(STEAMSPY_JSON):
        with open(STEAMSPY_JSON) as f:
            games_json = json.load(f)
    else:
        games_json = requests.get("http://steamspy.com/api.php?request=all").json()
        with open(STEAMSPY_JSON, "w") as f:
            json.dump(games_json, f, default=lambda o: o.__dict__, indent=2)
    for app_id, game in games_json.iteritems():
        if app_id == "999999":
            continue
        yield Game.from_steampspy_json(game)

def normalize(game_name):
    return game_name.lower().encode("ascii", "ignore").strip()

if __name__ == "__main__":
    for u in Game.get_unscored(5):
        u.update_userscore()
