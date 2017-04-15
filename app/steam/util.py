from os import path

data_dir = path.realpath(path.join(path.realpath(__file__), "..", "..", "..", "data"))

def data_file(filename):
    return path.join(data_dir, filename)
