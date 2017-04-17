from __future__ import print_function, division

import json
import os
import requests
import re

from . import Game
from app.dynamodb import dynamodb
from app.dynamodb.utils import create_dynamo_table, NUMBER
from boto3.dynamodb.conditions import Key
from collections import defaultdict

class TagReverseIndex(object):
    table_name = "tag_reverse_index"
    table = dynamodb.Table(table_name)
    hash_key = ("tag_id", NUMBER)
    sorting_key = None

    @classmethod
    def create_table(cls):
        create_dynamo_table(cls.table_name, cls.hash_key, cls.sorting_key)

    @classmethod
    def get_games_with_tags(cls, tags):
        if not (isinstance(tags, set) and len(tags) > 0):
            raise Exception("`tags` must be a non-empty set!")
        scanner = None
        for tag in tags:
            if scanner is None:
                scanner = Key(cls.hash_key[0]).eq(tag)
            else:
                scanner = scanner | Key(cls.hash_key[0]).eq(tag)
        response = cls.table.scan(FilterExpression=scanner)
        results = dict()
        for item in response["Items"]:
            results[int(item["tag_id"])] = map(int, item["game_ids"])
        while "LastEvaluatedKey" in response:
            response = cls.table.scan(FilterExpression=scanner,
                                      ExclusiveStartKey=response['LastEvaluatedKey'])
            for item in response["Items"]:
                results[int(item["tag_id"])] = map(int, item["game_ids"])
            results += response["Items"]
        return results

    @classmethod
    def batch_save(cls, index):
        with cls.table.batch_writer() as batch:
            for tag_id, game_ids in index.iteritems():
                entry = {cls.hash_key[0]: tag_id, "game_ids": game_ids}
                batch.put_item(Item=entry)

def compute_reverse_index():
    games = Game.get_all()
    tag_reverse_index = defaultdict(set)
    for game in games:
        for tag_id in game.tags:
            tag_reverse_index[int(tag_id)].add(int(game.app_id))
    return tag_reverse_index

if __name__ == '__main__':
    print(TagReverseIndex.get_games_with_tags(set([280, 154])))
