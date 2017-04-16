from __future__ import print_function

from . import dynamodb
from decimal import Decimal
from datetime import datetime, date

NUMBER = "N"
STRING = "S"

def create_dynamo_table(table_name, hash_key, sorting_key):
    matching_tables = [table for table in dynamodb.tables.all() if table.name == table_name]
    if len(matching_tables) != 0:
        print("Table", table_name, "already exists. Cannot create, skipping.")
    else:
        key_schema = [{'AttributeName': hash_key[0],
                       'KeyType': 'HASH'}]
        attribute_definitions = [{'AttributeName': hash_key[0],
                                  'AttributeType': hash_key[1]}]

        if sorting_key is not None:
            key_schema.append({'AttributeName': sorting_key[0],
                               'KeyType': 'RANGE'})
            attribute_definitions.append({'AttributeName': sorting_key[0],
                                          'AttributeType': sorting_key[1]})

        dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
