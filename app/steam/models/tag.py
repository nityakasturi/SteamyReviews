from __future__ import print_function, division

import csv
import json
import os
import requests
import re

from . import Game
from app.dynamodb import dynamodb, utils
from app.steam.util import data_file
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from collections import defaultdict
from decimal import Decimal

class TagMismatchException(Exception):
    def __init__(self, tag_name):
        super(TagMismatchException, self).__init__("Tag \"%s\" does not exist!"%tag_name)

class Tag(object):
    table_name = "tags"
    table = dynamodb.Table(table_name)
    hash_key = ("tag_name", utils.STRING)
    sorting_key = ("weight", utils.NUMBER)

    @classmethod
    def create_table(cls):
        utils.create_dynamo_table(cls)

    @classmethod
    def from_steamspy_row(cls, row, tag_reverse_index):
        tag_name = row[1].lower().strip()
        if tag_name not in tag_reverse_index:
            raise TagMismatchException(tag_name)
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
        return cls.from_json(dynamo_json)

    @classmethod
    def batch_save(cls, tags):
        return utils.batch_save(cls, tags)

    @classmethod
    def get_all(cls):
        return map(cls.from_dynamo_json, utils.table_scan(cls))

    @classmethod
    def get_games_with_tags(cls, tag_names):
        if not (isinstance(tag_names, set) and len(tag_names) > 0):
            raise Exception("`tag_names` must be a non-empty set!")
        scanner = None
        for tag in tag_names:
            if scanner is None:
                scanner = Key(cls.hash_key[0]).eq(tag)
            else:
                scanner = scanner | Key(cls.hash_key[0]).eq(tag)
        results = dict()
        for tag in utils.table_scan(cls, FilterExpression=scanner):
            results[item["tag_name"]] = map(int, item["app_ids"])
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
        tag_json = self.__dict__.copy()
        tag_json["app_ids"] = list(tag_json["app_ids"])
        return tag_json

    def to_dynamo_json(self):
        json = self.to_json()
        # str here is ghetto af but it's the only way not to get rounding errors
        json["price"] = Decimal(str(self.price))
        json["userscore"] = Decimal(str(self.userscore))
        return json

    def save(self):
        Tag.table.put_item(Item=self.to_dynamo_json())

def compute_reverse_index(games=None):
    if games is None:
        games = Game.get_all()
    tag_reverse_index = defaultdict(set)
    for game in games:
        for tag_name in game.tags:
            tag_reverse_index[tag_name.lower().strip()].add(int(game.app_id))
    return tag_reverse_index

def create_tag_list(tag_reverse_index):
    # No automatic way to get the CSV file from steamspy, has to be updated manually
    with open(data_file("steamspy.csv")) as f:
        reader = csv.reader(f)
        reader.next() # skip the header
        tags = [Tag.from_steamspy_row(row, tag_reverse_index) for row in reader]
    return tags
