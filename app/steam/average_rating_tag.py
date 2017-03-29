from __future__ import division

import requests
import json
import re

from bs4 import BeautifulSoup

tags_to_rating_sum = {}
tags_to_count = {}
baseString = "http://store.steampowered.com/app/"
review_to_score = {
    "Overwhelmingly Positive": 8,
    "Very Positive": 7,
    "Positive": 6,
    "Mostly Positive": 5,
    "Mixed": 4,
    "Mostly Negative": 3,
    "Negative": 2,
    "Very Negative": 1,
    "Overwhelmingly Negative": 0
}

def create_dicts_from_file(f):
    global tags_to_rating_sum
    tags_to_rating_sum= {}
    global tags_to_count
    tags_to_count = {}
    tags_list = json.load(f)
    for tag in tags_list:
        tags_to_rating_sum[tag['tag']] = 0
        tags_to_count[tag['tag']] = 0

def process_games(f):
    global tags_to_count
    global tags_to_rating_sum
    games = json.load(f)
    for game in games[:10]:
        link = baseString + game['app_id']
        page = requests.get(link)
        soup = BeautifulSoup(page.text, "lxml")
        overall_section = soup.find_all("div", class_="summary_section")
        #print(overall_section)
        if len(overall_section) == 0:
            continue
        for rating in overall_section:
            if (rating.text.find("Overall")):
                rating2 = rating.text.replace("\n", "").strip()
                print(rating2)


if __name__ == "__main__":
    with open("../../data/tags.json", 'r') as f:
        create_dicts_from_file(f)
    with open("../../data/app_ids.json", 'r') as g:
        process_games(g)
