from __future__ import print_function

import os

from argparse import ArgumentParser
from os import path
from subprocess import Popen, PIPE

MALLET_DIRECTORY = path.dirname(path.realpath(__file__))
DATA_DIRECTORY = path.join(path.dirname(MALLET_DIRECTORY), "data")

def data_file(*path_segments):
    return path.realpath(path.join(DATA_DIRECTORY, *path_segments))

def mallet_file(*path_segments):
    return path.realpath(path.join(MALLET_DIRECTORY, *path_segments))


def print_output(process):
    while process.poll() is None:
        print(process.stdout.readline())
    print(process.stdout.read())

def import_data(data_dir, mallet_data, token_regex, **kwargs):
    mallet_process = Popen(["mallet", "import-dir",
                            "--input", data_dir,
                            "--output", mallet_data,
                            "--token-regex", token_regex,
                            "--keep-sequence",
                            "--remove-stopwords",
                            "--extra-stopwords", mallet_file("extra_stopwords")],
                            stdout=PIPE, shell=True)
    print_output(mallet_process)

def train(input_file, model_path, num_topics, num_top_words, num_iterations, **kwargs):
    mallet_process = Popen(["mallet", "train-topics",
                            "--input", input_file,
                            "--num-topics", str(num_topics),
                            "--num-iterations", str(num_iterations),
                            "--output-doc-topics", path.join(model_path, "doc_matrix.tsv"),
                            "--output-topic-keys", path.join(model_path, "feature_keywords.tsv"),
                            "--num-top-words", str(num_top_words)], stdout=PIPE, shell=True)
    print_output(mallet_process)

def main():
    parser = ArgumentParser()
    parser.add_argument("model_name", help="Name for new model")

    parser.add_argument("-d", "-data-dir", type=str, dest="data_dir",
                        default=data_file("reviews_1000_tokens"),
                        help="Path to data. Defaults to `data/reviews_1000_tokens`")

    parser.add_argument("-m", "-mallet-data", type=str, dest="mallet_data",
                        default=mallet_file("reviews_1000.mallet"),
                        help="Path mallet data file. Defaults to `mallet/reviews_1000.mallet")

    parser.add_argument("-p", "--model-path", dest="model_path", type=str, nargs="?",
                        help="Path to model directory. Defaults to `mallet/{model_name}`")

    parser.add_argument("-n", "--num-topics", dest="num_topics", type=int, default=40,
                        help="Number of topics")

    parser.add_argument("-w", "--num-top-words", dest="num_top_words", type=int, default=20,
                        help="Number of words to output for each topics")

    parser.add_argument("-i", "--num-iterations", dest="num_iterations", type=int, default=1000,
                        help="Number of Mallet iterations")

    parser.add_argument("--token-regex", dest="token_regex", type=str, default="\\p{L}+",
                        help="Regex to use when tokenizing documents")

    args = parser.parse_args()

    if args.model_path is None:
        args.model_path = mallet_file(args.model_name)

    if not path.exists(args.model_path):
        os.mkdir(args.model_path)

    if not path.exists(args.mallet_data):
        import_data(**vars(args))
    train(input_file=args.mallet_data, **vars(args))

if __name__ == '__main__':
    main()
