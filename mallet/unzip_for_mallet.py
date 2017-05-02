import json
import re

from argparse import ArgumentParser
from nltk.tokenize import word_tokenize
from os import path

THIS_DIRECTORY = path.dirname(path.realpath(__file__))
DATA_DIR = path.join(path.dirname(THIS_DIRECTORY), "data")
TOKEN_RE = re.compile(r"([a-z0-9]+((-|/)[a-z0-9]+)?)")

def num_tokens(body):
    review_str = body.encode('ascii', 'ignore')
    tokens = word_tokenize(review_str)
    token_count = 0
    for token in tokens:
        lower_token = token.lower()
        match = TOKEN_RE.match(lower_token)

        # verify that the regex matches the whole token
        if match != None and match.group(0) == lower_token:
            if '/' in lower_token:
                token_count += len(lower_token.split('/'))
            else:
                token_count += 1

    return token_count

def main(min_reviews, max_tokens, **kwargs):
    with open(path.join(DATA_DIR, "uncompressed_reviews.json"), "r") as f:
        reviews = json.load(f)
    app_ids = reviews.keys()
    for app_id in app_ids:
        if len(reviews[app_id]) >= min_reviews:
            with open(path.join(DATA_DIR, "reviews_%d_tokens"%max_tokens, str(app_id)), "w") as f:
                toks = 0
                for r in reviews[app_id]:
                    if toks > max_tokens:
                        break
                    else:
                        toks += num_tokens(r["body"])
                        f.write(r["body"].encode("ascii", "ignore"))
                    f.write("\n")
        del reviews[app_id]

def count_reviews():
    with open(path.join(DATA_DIR, "unfiltered_uncompressed_reviews.json"), "r") as f:
        reviews = json.load(f)
    with open("app_id_to_num_reviews.csv", "w") as f:
        for app_id, reviews in reviews.iteritems():
            f.write("%s,%s\n"%(app_id, len(reviews)))

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-m", "--min-reviews", dest="min_reviews", type=int, default=250,
                        help="Minimum number of reviews per game")
    parser.add_argument("-t", "--max-tokens", dest="max_tokens", type=int, default=1000,
                        help="Maximum number of tokens per file")
    args = parser.parse_args()
    # main(**vars(args))
    count_reviews()


