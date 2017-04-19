from os import path
from app import dynamodb

data_dir = path.realpath(path.join(path.realpath(__file__), "..", "..", "..", "data"))

def data_file(filename):
    return path.join(data_dir, filename)
