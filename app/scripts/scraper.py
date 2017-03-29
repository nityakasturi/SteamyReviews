# Slightly adapted from https://github.com/dmn001/steam_review_scraper

import requests
from bs4 import BeautifulSoup
import codecs
import unicodecsv
import sys
import re

# day_range = '9223372036854776000'

people_re = "(?:person|people)"

helpful_re = re.compile("(\d+) of (\d+) " + people_re)
funny_re = re.compile("(\d+) " + people_re)
on_record_re = re.compile("(\d+\.?\d*) hrs? on record")
products_re = re.compile("(\d+) products? in account")
reviews_re = re.compile("(\d+) reviews?")

class Review(object):
    def __init__(self, app_id, review_id, review_soup):
        self.app_id = app_id
        self.review_soup = review_soup
        self.body = self._find_div_text("content")
        self.reviewer = self._find_div_text("persona_name")
        self.date = self._find_div_text("postedDate")

        header = self._find_div_text("header")
        for line in header.split("\n"):
            line = line.lower()
            if "helpful" in line:
                match = helpful_re.match(line)
                if match is not None:
                    self.helpful, self.total = map(int, match.groups())
            if "funny" in line:
                match = funny_re.match(line)
                if match is not None:
                    self.funny, = map(int, match.groups())

        self.recommended = "thumbsup" in self.review_soup.find("div", class_="thumb").find("img")["src"].lower()

        match = on_record_re.match(self._find_div_text("hours"))
        if match is not None:
            self.on_record, = map(float, match.groups())

        match = products_re.match(self._find_div_text("num_owned_games"))
        if match is not None:
            self.num_owned_games, = map(float, match.groups())

        match = reviews_re.match(self._find_div_text("num_reviews"))
        if match is not None:
            self.num_reviews, = map(float, match.groups())

        avatar_url = self.review_soup.find("div", class_="avatar").find("a")["href"]
        self.reviewer_id = filter(lambda s: len(s) > 0, avatar_url.split("/"))[-1]

        del self.review_soup

    def _find_div_text(self, div_class):
        return self.review_soup.find('div', class_=div_class).get_text("\n", strip=True)

def get_app_reviews(app_id,
                    max_reviews=1000,
                    filter="all",
                    offset=0,
                    language="english"):
    reviews = dict()
    params = {
        # "day_range": day_range,
        "filter": filter,
        "language": language
    }
    offset = 0
    while len(reviews) < max_reviews:
        params["start_offset"] = offset
        url = "http://store.steampowered.com/appreviews/%s"%app_id
        r = requests.get(url, params=params)

        json = r.json()
        if json.get('success') != 1:
            break

        soup = BeautifulSoup(json['html'], "lxml")
        review_box = soup.find_all('div',class_="review_box")
        for review_id, review in zip(json['recommendationids'], review_box):
            reviews[review_id] = Review(app_id, review_id, review)

        # The way offset increases needs to be verified
        if offset == 0:
            offset = 5
        elif offset == 5:
            offset = 25
        else:
            offset += 25
    return reviews

reviews = get_app_reviews("396750", 5)
