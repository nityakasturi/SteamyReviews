from __future__ import print_function, division

import csv
import json
import os
import requests
import re

from . import Game
from app.dynamodb import db, utils
from app.models.game import iter_all_games
from app.utils import data_file
from bs4 import BeautifulSoup as BS
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

class TagDoesNotExistException(Exception):
    def __init__(self, tag_name):
        super(TagDoesNotExistException, self).__init__("Tag \"%s\" does not exist!"%tag_name)

class Tag(object):
    table_name = "tags"
    table = db.Table(table_name)
    hash_key = ("tag_name", utils.STRING)
    sorting_key = ("weight", utils.NUMBER)

    __tag_cache = None
    __last_refresh = None

    @classmethod
    def from_steamspy_row(cls, row, tag_reverse_index):
        tag_name = row[1].lower().strip()
        if tag_name not in tag_reverse_index:
            raise TagDoesNotExistException(tag_name)
        # count, votes, weight
        row[2:5] = [int(s.replace(",", "")) for s in row[2:5]]
        # price
        row[5] = float(row[5].replace("$", ""))
        # userscore
        row[6] = float(row[6].replace("%", ""))
        # owners
        row[7] = int(row[7].replace(",", ""))

        return cls(tag_name=tag_name,
                   count=row[2],
                   votes=row[3],
                   weight=row[4],
                   price=row[5],
                   userscore=row[6],
                   owners=row[7],
                   app_ids=tag_reverse_index[tag_name])

    @classmethod
    def from_json(cls, tag_json):
        tag_json["app_ids"] = set(tag_json["app_ids"])
        return cls(**tag_json)

    @classmethod
    def from_dynamo_json(cls, dynamo_json):
        dynamo_json["price"] = float(dynamo_json["price"])
        dynamo_json["userscore"] = float(dynamo_json["userscore"])
        dynamo_json["app_ids"] = map(int, dynamo_json["app_ids"])
        return cls.from_json(dynamo_json)

    @classmethod
    def batch_save(cls, tags):
        return utils.batch_save(cls, tags)

    @classmethod
    def get_all(cls):
        return map(cls.from_dynamo_json, utils.table_scan(cls))

    @classmethod
    def __refresh_cache(cls):
        if (cls.__tag_cache is None
            or cls.__last_refresh is None
            # refresh the cache if it's more than 24 hours old
            or (cls.__last_refresh - datetime.now()).total_seconds() > 24 *3600):
            # games = list(iter_all_games())
            tag_reverse_index = compute_reverse_index(iter_all_games())
            tags = create_tag_list(tag_reverse_index)
            # tags = cls.get_all()
            cls.__tag_cache = {tag.tag_name: tag for tag in tags}
            cls.__last_refresh = datetime.now()

    @classmethod
    def get(cls, tag_name):
        cls.__refresh_cache()
        if tag_name in cls.__tag_cache:
            return cls.__tag_cache[tag_name]
        else:
            raise TagDoesNotExistException(tag_name)

    @classmethod
    def get_games_with_tags(cls, tag_names):
        cls.__refresh_cache()
        if not (isinstance(tag_names, set) and len(tag_names) > 0):
            raise Exception("`tag_names` must be a non-empty set!")
        results = dict()
        for tag_name in tag_names:
            results[tag_name] = cls.get(tag_name).app_ids
        return results

    def __init__(self, tag_name, count, votes, weight, price, userscore, owners, app_ids):
        self.tag_name = tag_name
        self.count = count
        self.votes = votes
        self.weight = weight
        self.price = price
        self.userscore = userscore
        self.owners = owners
        self.app_ids = app_ids

    def to_json(self):
        return {
            "tag_name": self.tag_name,
            "count": self.count,
            "votes": self.votes,
            "weight": self.weight,
            "price": self.price,
            "userscore": self.userscore,
            "owners": self.owners,
            "app_ids": list(self.app_ids),
        }

    def to_dynamo_json(self):
        dynamo_json = self.to_json()
        dynamo_json["price"] = Decimal(str(self.price))
        dynamo_json["userscore"] = Decimal(str(self.userscore))
        return dynamo_json

    def save(self):
        Tag.table.put_item(Item=self.to_dynamo_json())

def compute_reverse_index(games=None):
    if games is None:
        games = Game.get_all()
    tag_reverse_index = defaultdict(set)
    for game in games:
        if len(game.tags) > 0:
            for tag_name in game.tags:
                tag_reverse_index[tag_name.lower().strip()].add(int(game.app_id))
    return tag_reverse_index

STEAMSPY_TAG_CSV = data_file("steamspy_tags.csv")
def create_tag_list(tag_reverse_index):
    if not os.path.exists(STEAMSPY_TAG_CSV):
        page = requests.get("http://steamspy.com/tag/").text
        soup = BS(page, "lxml")
        table = soup.find("table", id="gamesbygenre")
        table_head = table.find("thead")
        table_body = table.find("tbody")
        with open(STEAMSPY_TAG_CSV, "w") as f:
            writer = csv.writer(f)
            # write CSV header, just because
            writer.writerow(list(table_head.stripped_strings))
            writer.writerows(list(row.stripped_strings) for row in table_body.find_all("tr"))
    with open(STEAMSPY_TAG_CSV) as f:
        reader = csv.reader(f)
        reader.next() # skip the header
        return [Tag.from_steamspy_row(row, tag_reverse_index) for row in reader]
