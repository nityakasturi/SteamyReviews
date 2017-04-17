from __future__ import print_function

from . import dynamodb
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime, date

NUMBER = "N"
STRING = "S"

def create_dynamo_table(cls):
    matching_tables = [table for table in dynamodb.tables.all() if table.name == cls.table_name]
    if len(matching_tables) != 0:
        print("Table", cls.table_name, "already exists. Cannot create, skipping.")
    else:
        key_schema = [{'AttributeName': cls.hash_key[0],
                       'KeyType': 'HASH'}]
        attribute_definitions = [{'AttributeName': cls.hash_key[0],
                                  'AttributeType': cls.hash_key[1]}]

        if cls.sorting_key is not None:
            key_schema.append({'AttributeName': cls.sorting_key[0],
                               'KeyType': 'RANGE'})
            attribute_definitions.append({'AttributeName': cls.sorting_key[0],
                                          'AttributeType': cls.sorting_key[1]})

        dynamodb.create_table(
            TableName=cls.table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

def batch_save(cls, items):
    failed = list()
    try:
        print("---- BEGIN `%s` BATCH SAVE ----"%cls.table_name)
        with cls.table.batch_writer() as batch:
            for item in items:
                try:
                    batch.put_item(Item=item.to_dynamo_json())
                except ClientError as e:
                    failed.append(item)
                    print("---- FAILED `%s` BATCH SAVE ----"%cls.table_name,
                          item.to_dynamo_json(),
                          e,
                          sep="\n")
    except ClientError as e:
        print("There were some failures while ", e)
        print("---- END FAILED `%s` BATCH SAVE ----"%cls.table_name)
        return failed
    else:
        print("---- END SUCCESFUL `%s` BATCH SAVE ----"%cls.table_name)
        return list()
