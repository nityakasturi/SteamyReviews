from __future__ import division

import requests
import json

from bs4 import BeautifulSoup


def get_all_tags():
    """
    Gets all tags from the tag page of steamdb
    """
    results = []
    page = requests.get("https://steamdb.info/tags/")
    soup = BeautifulSoup(page.text, "lxml")
    for div in soup.find_all("div", class_="span4"):
        outcome = {}
        product = int(div.find(
            "span", class_="label-count pull-right muted").string.strip().replace("products", ""))
        outcome['count'] = product
        tag = div.find("a", class_="label label-link").contents[2].strip().replace("\n", "")
        outcome['tag'] = tag
        results.append(outcome)
    return results

if __name__ == '__main__':
    tags = get_all_tags()
    with open("../../data/tags.json", 'w') as f:
        json.dump(tags, f, indent=2)
