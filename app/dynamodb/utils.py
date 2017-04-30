from __future__ import print_function

from app import db
from botocore.exceptions import ClientError
from progressbar import ProgressBar, UnknownLength

NUMBER = "N"
STRING = "S"

def create_dynamo_table(cls):
    matching_tables = [table for table in db.tables.all() if table.name == cls.table_name]
    if len(matching_tables) != 0:
        print("Table `%s` already exists. Cannot create, skipping."%cls.table_name)
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

        db.create_table(
            TableName=cls.table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )

def batch_save(cls, items):
    if not hasattr(items, "__iter__"):
        raise ValueError("`items` must be iterable!")
    max_value = len(items) if hasattr(items, "__len__") else UnknownLength
    failed = list()
    try:
        print("---- BEGIN `%s` BATCH SAVE ----"%cls.table_name)
        with cls.table.batch_writer() as batch:
            count = 0
            with ProgressBar(max_value=max_value) as progress:
                for item in items:
                    try:
                        batch.put_item(Item=item.to_dynamo_json())
                    except ClientError as e:
                        failed.append(item)
                        print("---- FAILED `%s` BATCH SAVE ----"%cls.table_name,
                              item.to_dynamo_json(),
                              e,
                              sep="\n")
                    finally:
                        progress.update(count)
                        count += 1
    except ClientError as err:
        print("There were some failures while ", err)
        print("---- END FAILED `%s` BATCH SAVE ----"%cls.table_name)
        return failed
    else:
        print("---- END SUCCESFUL `%s` BATCH SAVE ----"%cls.table_name)
        return list()

def table_scan(cls, **kwargs):
    response = cls.table.scan(**kwargs)
    for item in response["Items"]:
        yield item
    while "LastEvaluatedKey" in response:
        response = cls.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], **kwargs)
        for item in response["Items"]:
            yield item

def query(cls, **kwargs):
    response = cls.table.query(**kwargs)
    for item in response["Items"]:
        yield item
    while "LastEvaluatedKey" in response:
        response = cls.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], **kwargs)
        for item in response["Items"]:
            yield item
