from __future__ import print_function, division, unicode_literals

import bs4
import decimal
import json
import requests
import re

from app.dynamodb import dynamodb, utils
from app.steam.util import data_file
from bs4 import BeautifulSoup as BS
from datetime import datetime
from nltk.tokenize import word_tokenize
from progressbar import ProgressBar
from random import getrandbits

people_re_part = r"(?:person|people)"
helpful_re = re.compile(r"(-?[0-9,]+) of ([0-9,]+) " + people_re_part)
funny_re = re.compile(r"(-?[0-9,]+) " + people_re_part)
on_record_re = re.compile(r"(-?[0-9,]+\.?\d*) hrs? on record")
products_re = re.compile(r"(-?[0-9,]+) products? in account")
reviews_re = re.compile(r"(-?[0-9,]+) reviews?")
token_re = re.compile(r"([a-z0-9]+((-|/)[a-z0-9]+)?)")

YEAR = datetime.now().year
EMPTY_DIV = bs4.element.Tag(name="")
MAX_REVIEWS = 250

class Review(object):
    table_name = "reviews"
    table = dynamodb.Table(table_name)
    hash_key = ("app_id", utils.NUMBER)
    sorting_key = ("review_date_review_id", utils.STRING)

    @classmethod
    def create_table(cls):
        utils.create_dynamo_table(cls)

    @classmethod
    def from_review_soup(cls, app_id, review_soup):
        review = {
            "app_id": app_id
        }

        url_re = r"^(?:https?://)w*\.?steamcommunity\.com/(.*)/recommended/"+ str(app_id) +"/?$"
        match = re.match(url_re, review_soup.get("data-modal-content-url"))
        if match is not None:
            review["review_id"], = match.groups()
        else:
            review["review_id"] = str(getrandbits(32))

        content = review_soup.find("div", class_="apphub_CardTextContent")
        review["body"] = " ".join(c.strip() for c in content.children
                                  if not isinstance(c, bs4.element.Tag) and len(c.strip()) > 0)

        review_date_div = content.find("div", class_="date_posted") or EMPTY_DIV
        review["review_date"] = parse_review_date(review_date_div.get_text(strip=True))


        is_recommended_div = review_soup.find("div", class_="title") or EMPTY_DIV
        review["is_recommended"] = is_recommended_div.get_text(strip=True).lower() == "recommended"

        helpful_div = review_soup.find("div", class_="found_helpful") or EMPTY_DIV
        matches = helpful_re.match(helpful_div.get_text(strip=True))
        if matches is not None:
            review["helpful"], review["total"] = (int(g.replace(",", "")) for g in matches.groups())
        else:
            review["helpful"], review["total"] = 0, 0

        hours_div = review_soup.find("div", class_="hours") or EMPTY_DIV
        matches = on_record_re.match(hours_div.get_text(strip=True))
        if matches is not None:
            review["on_record"], = (float(g.replace(",", "")) for g in matches.groups())
        else:
            review["on_record"] = 0

        return cls(**review)

    @classmethod
    def from_json(cls, json):
        json["review_date"] = datetime.strptime(json["review_date"], "%Y-%m-%d").date()
        return cls(**json)

    @classmethod
    def get_reviews_from_steam(cls, app_id):
        reviews = list()
        review_generator = (review_soup
                            for soup in iterate_review_pages(app_id, language="english")
                            for review_soup in soup.find_all("div", class_="apphub_Card"))
        with ProgressBar(max_value=MAX_REVIEWS) as progress:
            for review_soup in review_generator:
                review = cls.from_review_soup(app_id, review_soup)
                if len(review.get_tokens()) >= 20:
                    reviews.append(review)
                    if len(reviews) == MAX_REVIEWS:
                        break
                progress.update(len(reviews))
        return reviews

    @classmethod
    def from_dynamo_json(cls, dynamo_json):
        dynamo_json["on_record"] = float(dynamo_json["on_record"])
        return cls.from_json(dynamo_json)

    @classmethod
    def batch_save(cls, reviews):
        return utils.batch_save(cls, reviews)

    @classmethod
    def get(cls, key_condition, filter_expression, max_items, ascending=False):
        kwargs = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": ascending # get reviews in descending chronological order
        }
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if max_items is not None:
            kwargs["Limit"] = max_items

        return map(cls.from_dynamo_json, utils.query(cls, **kwargs))

    def __init__(self, app_id, review_id, review_date, body, helpful, total, is_recommended,
                 on_record, **kwargs):
        self.app_id = app_id
        self.review_id = review_id
        self.review_date = review_date
        self.review_date_review_id = self.review_date.isoformat() + ":" + str(self.review_id)
        self.body = body
        self.helpful = helpful
        self.total = total
        self.is_recommended = is_recommended
        self.on_record = on_record

    def __repr__(self):
        return "Review(app_id=%d,review_id=%s)"%(self.app_id, self.review_id)

    def __str__(self):
        return self.__repr__()

    def to_json(self):
        return {
            "app_id": self.app_id,
            "review_id": self.review_id,
            "review_date": self.review_date.isoformat(),
            "review_date_review_id": self.review_date_review_id,
            "body": self.body,
            "helpful": self.helpful,
            "total": self.total,
            "is_recommended": self.is_recommended,
            "on_record": self.on_record,
        }

    def to_dynamo_json(self):
        dynamo_json = self.to_json()
        # str here is ghetto af but it's the only way not to get rounding errors
        dynamo_json["on_record"] = decimal.Decimal(str(self.on_record))
        for k in dynamo_json:
            if dynamo_json[k] == "":
                dynamo_json[k] = None
        return dynamo_json

    def save(self):
        Review.table.put_item(Item=self.to_dynamo_json())

    def get_tokens(self):
        punc_regex = r'[!\"#\$%&\'\(\)\*\+,-\./:;<=>\?@\[\\\]\^_`{\|}~]+'
        # excludes situations such as boy-friend/girl-friend - but inconsequential

        review_str = self.body.encode('ascii', 'ignore')
        tokens = word_tokenize(review_str)
        filtered_tokens = []
        for token in tokens:
            lower_token = token.lower()
            match = token_re.match(lower_token)

            # verify that the regex matches the whole token
            if match != None and match.group(0) == lower_token:
                if '/' in lower_token:
                    for elem in lower_token.split('/'):
                        filtered_tokens.append(elem)
                else:
                    filtered_tokens.append(lower_token)

        return filtered_tokens

def parse_review_date(date_text):
    if date_text is None or len(date_text) == 0:
        date_text = "Posted: July 20, 1969"

    try:
        return datetime.strptime(date_text, "Posted: %B %d, %Y").date()
    except ValueError:
        # Reviews left in this year don't have a date, so we just default to this year's date
        return datetime.strptime(date_text, "Posted: %B %d").date().replace(year=YEAR)

more_content_re = re.compile(r"MoreContentForm\d+")
def iterate_review_pages(app_id, language="english"):
    url = "http://steamcommunity.com/app/%d/reviews"%app_id
    params = {
        "browsefilter": "toprated",
        "filterLanguage": language
    }
    first_page = requests.get(url, params)
    soup = BS(first_page.text, "lxml")
    yield soup
    while True:
        form = soup.find("form", id=more_content_re)
        if form is not None:
            form_url = form.get("action")
            params = dict()
            for param in form.find_all("input"):
                params[param.get("name")] = param.get("value")
            next_page = requests.get(form_url, params)
            soup = BS(next_page.text, "lxml")
            yield soup
        else:
            break

def saved_review_generator():
    import json
    reviews_file = data_file("reviews.json")
    with open(reviews_file) as f:
        reviews = json.load(f)
    for app_id in reviews:
        for i in xrange(len(reviews[app_id])):
            yield Review.from_json(reviews[app_id][i])
