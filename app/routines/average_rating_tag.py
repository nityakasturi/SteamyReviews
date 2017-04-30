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
average = {}

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
    overall_re = r'Overall:([A-Za-z ]+)'
    for game in games[:1000]:
        link = baseString + game['app_id']
        page = requests.get(link)
        soup = BeautifulSoup(page.text, "lxml")
        #for tag in tags_section.find_all("a"):

        overall_section = soup.find_all("div", class_="summary_section")
        #print(overall_section)
        if overall_section is None or len(overall_section) == 0:
            continue
        for rating in overall_section:
            if (rating.text.find("Overall") > 0):
                rating2 = rating.text.replace("\n", "").strip()
                match = re.match(overall_re, rating2)
                review = match.groups()[0]
                score = review_to_score[review]
                tags_section = soup.find("div", class_="glance_tags popular_tags")
                #print(tags_section.find_all("a"))
                if (tags_section is None or len(tags_section) ==  0):
                    continue
                for tag in tags_section.find_all("a"):
                    trimmed_tag = tag.text.replace("\r", "").replace("\n", "").replace("\t", "").strip()
                    if trimmed_tag in tags_to_count:
                        tags_to_count[trimmed_tag] += 1
                        tags_to_rating_sum[trimmed_tag] += score

def average_reviews():
    global tags_to_count
    global tags_to_rating_sum
    global average
    for key in tags_to_count:
        if (tags_to_count[key] > 0):
            average[key] = tags_to_rating_sum[key] / tags_to_count[key]
    with open("../../ratings_per_tag.json", "w") as f:
        json.dump(average, f, indent=2)


if __name__ == "__main__":
    with open("../../data/tags.json", 'r') as f:
        create_dicts_from_file(f)
    with open("../../data/app_ids.json", 'r') as g:
        process_games(g)
        average_reviews()
