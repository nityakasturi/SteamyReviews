from __future__ import print_function, division

import json
import requests
import re

from app.dynamodb import dynamodb
from app.dynamodb.utils import create_dynamo_table, STRING, NUMBER
from bs4 import BeautifulSoup
from decimal import Decimal

review_to_score = {
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
score_to_review = {score: r for r,score in review_to_score.iteritems()}

class Game(object):
    table_name = "apps"
    table = dynamodb.Table(table_name)
    hash_key = ("app_id", NUMBER)
    sorting_key = None

    @classmethod
    def create_table(cls):
        create_dynamo_table(Game.table_name, Game.hash_key, Game.sorting_key)

    @classmethod
    def from_table_row(cls, table_row):
        columns = map(lambda td: td.get_text(strip=True),
                      table_row.find_all("td"))
        return cls(app_id=columns[1],
                   name=columns[2])

    @classmethod
    def from_json(cls, json):
        return cls(**json)

    @classmethod
    def batch_save(cls, games):
        with cls.table.batch_writer() as batch:
            for g in games:
                batch.put_item(Item=g.to_json())

    def __init__(self, app_id, name, developer, publisher, owners, score_rank, price, tags):
        self.app_id = app_id
        self.name = name
        self.developer = developer
        self.publisher = publisher
        self.owners = owners
        self.score_rank = score_rank
        self.price = float(price) / 100 # price is in cents
        self.tags = tags

    def to_json(self):
        return self.__dict__.copy()

    def to_dynamo_json(self):
        json = self.to_json()
        json["price"] = Decimal(str(self.price))
        return json

    def save(self):
        Game.table.put_item(Item=self.to_json())

def iter_all_games():
    games_json = json.loads(requests.get("http://steamspy.com/api.php?request=all").text)
    for app_id, game in games_json.iteritems():
        if app_id == "999999":
            continue
        del game["appid"]
        del game["owners_variance"]
        del game["players_forever"]
        del game["players_forever_variance"]
        del game["players_2weeks"]
        del game["players_2weeks_variance"]
        del game["average_forever"]
        del game["average_2weeks"]
        del game["median_forever"]
        del game["median_2weeks"]
        del game["ccu"]

        game["app_id"] = int(app_id)
        # flip the key/value so it matches better with the other data structures
        tags = {id: name for name, id in game["tags"]}
        game["tags"] = tags
        yield Game(**game)

def get_app_ids_from_graph_page():
    graph = requests.get("https://steamdb.info/graph/")
    soup = BeautifulSoup(graph.text, "lxml")
    table = soup.find("table", id="table-apps").find("tbody")
    return sorted(map(Game.from_table_row, table.find_all("tr", class_="app")),
                  key=lambda g: g.name)

if __name__ == '__main__':
    Game.batch_save(iter_all_games())
