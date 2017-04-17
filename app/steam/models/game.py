from __future__ import print_function, division

import json
import os
import requests
import re

from . import Review
from app.dynamodb import dynamodb
from app.dynamodb.utils import create_dynamo_table, STRING, NUMBER
from app.steam.util import data_file
from bs4 import BeautifulSoup
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from decimal import Decimal

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


class Game(object):
    table_name = "apps"
    table = dynamodb.Table(table_name)
    hash_key = ("app_id", NUMBER)
    sorting_key = None

    @classmethod
    def create_table(cls):
        create_dynamo_table(Game.table_name, Game.hash_key, Game.sorting_key)

    @classmethod
    def from_steampspy_json(cls, app_id, game):
        # We don't use any of these guys so we have to delete them
        game.pop("appid", None)
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

        game["app_id"] = int(app_id)
        game["price"] = float(game["price"] or 0) / 100 # price is in cents

        if game["developer"] is None or len(game["developer"]) == 0:
            game["developer"] = None
        if game["publisher"] is None or len(game["publisher"]) == 0:
            game["publisher"] = None

        # flip the key/value so it matches better with the other data structures
        if len(game["tags"]) > 0:
            tags = {str(tag_id): name for name, tag_id in game["tags"].iteritems()}
        else:
            tags = {}
        game["tags"] = tags

        # we have to set the actual userscore and num_reviews to -1 because this API doesn't return
        # those values
        game["userscore"] = -1
        game["num_reviews"] = -1
        return cls(**game)

    @classmethod
    def from_json(cls, game_json):
        return cls(**game_json)

    @classmethod
    def from_dynamo_json(cls, dynamo_json):
        dynamo_json["price"] = float(dynamo_json["price"])
        return cls(**dynamo_json)

    @classmethod
    def batch_save(cls, games):
        failed = list()
        try:
            print("---- BEGIN BATCH SAVE ----")
            with cls.table.batch_writer() as batch:
                for g in games:
                    try:
                        batch.put_item(Item=g.to_dynamo_json())
                    except ClientError as e:
                        failed.append(g)
                        print("---- FAILED BATCH SAVE ----",
                              g.to_dynamo_json(),
                              e,
                              sep="\n")
        except ClientError as e:
            print("There were some failures while ", e)
            print("---- END BATCH SAVE ----")
            return failed

    @classmethod
    def get(cls, app_id):
        res = cls.table.get_item(Key={cls.hash_key[0]: app_id})
        if "Item" in res:
            return cls.from_dynamo_json(res["Item"])
        else:
            raise GameNotFoundException(app_id)

    @classmethod
    def get_all(cls):
        response = cls.table.scan()
        results = map(cls.from_dynamo_json, response["Items"])
        while "LastEvaluatedKey" in response:
            response = cls.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            results += map(cls.from_dynamo_json, response["Items"])
        return results

    @classmethod
    def get_unscored(cls, limit=1000):
        attr_cond = Attr("userscore").eq(-1)
        response = cls.table.scan(FilterExpression=attr_cond, Limit=limit)
        results = map(cls.from_dynamo_json, response["Items"])
        while "LastEvaluatedKey" in response and len(results) < limit:
            response = cls.table.scan(FilterExpression=attr_cond,
                                      Limit=5,
                                      ExclusiveStartKey=response['LastEvaluatedKey'])
            results += map(cls.from_dynamo_json, response["Items"])
        return results


    def __init__(self, app_id, name, developer, publisher, owners, userscore, num_reviews,
                 score_rank, price, tags):
        self.app_id = app_id
        self.name = name
        self.developer = developer
        self.publisher = publisher
        self.owners = owners
        self.userscore = userscore
        self.num_reviews = num_reviews
        self.score_rank = score_rank
        self.price = price
        self.tags = tags

    def to_json(self):
        return self.__dict__.copy()

    def to_dynamo_json(self):
        dynamo_json = self.to_json()
        dynamo_json["price"] = Decimal(str(self.price))
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

    def update_userscore(self):
        page = requests.get("http://store.steampowered.com/app/%s"%self.app_id)
        soup = BeautifulSoup(page.text)

        summary_section = soup.find_all("div", class_="summary_section")
        for sec in summary_section:
            title, score, num_reviews = sec.stripped_strings
            if "overall" in title.lower():
                matches = reviews_re.match(num_reviews)
                if score in userscore_to_digit and matches is not None:
                    self.userscore = userscore_to_digit[score]
                    num_reviews, = matches.groups()
                    self.num_reviews = int(num_reviews.replace(",", ""))
                    self.save()
                    print("Succesfully updated userscore for", self.app_id)
                    return

        print("Could not update userscore for", self.app_id)

def iter_all_games():
    games_json = requests.get("http://steamspy.com/api.php?request=all").json()
    for app_id, game in games_json.iteritems():
        if app_id == "999999":
            continue
        yield Game.from_steampspy_json(app_id, game)

if __name__ == '__main__':
    for u in Game.get_unscored(5):
        u.update_userscore()
