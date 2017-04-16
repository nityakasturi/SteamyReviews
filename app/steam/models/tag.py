from __future__ import print_function, division

import csv
import json
import os
import requests
import re

from app.dynamodb import dynamodb
from app.dynamodb.utils import create_dynamo_table, STRING, NUMBER
from app.steam.util import data_dir
from decimal import Decimal

class Tag(object):
    table_name = "tags"
    table = dynamodb.Table(table_name)
    hash_key = ("tag_id", NUMBER)
    sorting_key = ("weight", NUMBER)

    @classmethod
    def create_table(cls):
        create_dynamo_table(cls.table_name, cls.hash_key, cls.sorting_key)

    @classmethod
    def from_steamspy_row(cls, row):
        row[0] = int(row[0])
        # count, votes, weight
        row[2:5] = [int(s.replace(",", "")) for s in row[2:5]]
        # price
        row[5] = float(row[5].replace("$", ""))
        # userscore
        row[6] = float(row[6].replace("%", ""))
        # owners
        row[7] = int(row[7].replace(",", ""))

        return cls(tag_id=int(row[0]),
                   name=row[1],
                   count=row[2],
                   votes=row[3],
                   weight=row[4],
                   price=row[5],
                   userscore=row[6],
                   owners=row[7])

    @classmethod
    def from_json(cls, json):
        return cls(**json)

    @classmethod
    def from_dynamo_json(cls, dynamo_json):
        dynamo_json["price"] = float(dynamo_json["price"])
        dynamo_json["userscore"] = float(dynamo_json["userscore"])
        return cls.from_json(dynamo_json)

    @classmethod
    def batch_save(cls, tags):
        with cls.table.batch_writer() as batch:
            for t in tags:
                print(t.to_dynamo_json())
                batch.put_item(Item=t.to_dynamo_json())

    def __init__(self, tag_id, name, count, votes, weight, price, userscore, owners):
        self.tag_id = tag_id
        self.name = name
        self.count = count
        self.votes = votes
        self.weight = weight
        self.price = price
        self.userscore = userscore
        self.owners = owners

    def to_json(self):
        return self.__dict__.copy()

    def to_dynamo_json(self):
        json = self.to_json()
        # str here is ghetto af but it's the only way not to get rounding errors
        json["price"] = Decimal(str(self.price))
        json["userscore"] = Decimal(str(self.userscore))
        return json

    def save(self):
        Tag.table.put_item(Item=self.to_dynamo_json())

def get_tags():
    # No automatic way to get the CSV file from steamspy, has to be updated manually
    with open(os.path.join(data_dir, "steamspy.csv")) as f:
        reader = csv.reader(f)
        reader.next() # skip the header
        tags = map(Tag.from_steamspy_row, reader)
    return tags

if __name__ == '__main__':
    Tag.batch_save(get_tags())
