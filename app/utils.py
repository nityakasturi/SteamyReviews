from os import path

ROOT = path.join(path.realpath(__file__), "..", "..")
DATA_DIR = path.realpath(path.join(ROOT, "data"))
MALLET_DIR = path.realpath(path.join(ROOT, "mallet"))

def data_file(*path_segments):
    return path.join(DATA_DIR, *path_segments)

def mallet_file(*path_segments):
    return path.join(MALLET_DIR, *path_segments)
