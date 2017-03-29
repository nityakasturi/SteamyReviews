from __future__ import print_function, division
import requests
from bs4 import BeautifulSoup
import json
import sys

max_pages = 750

def get_apps_page(page_number):
    if not 1 <= page_number <= max_pages:
        msg = "page_number must be between 1 and 750! Was %d"%page_number
        raise Exception(msg)
    url = "https://steamdb.info/apps/page%d/"%page_number
    res = requests.get(url)
    if not 200 <= res.status_code < 300:
        msg = "Invalid status code (%d) when fetching page %d"%(res.status_code,
                                                                page_number)
        raise Exception(msg)
    return res.text

def extract_app_ids(page, apps=dict()):
    soup = BeautifulSoup(page, "lxml").find_all("tr", class_="app")
    for app in soup:
        i = app.find_all("i", class_="subinfo")
        if not (len(i) > 0 and i[0].text == "Game"):
            continue
        app_id = app["data-appid"]
        title = app.find_all("a", class_="b")[0].text
        apps[app_id] = title
    return apps

def save_app_ids(apps, filename="app_ids.json"):
    with open("app_ids.json", 'w') as f:
        json.dump(apps, f)

if __name__ == '__main__':
    # First parameter (optional) says how many pages to scan
    if len(sys.argv) > 1:
        max_pages = int(sys.argv[1])
    apps = dict()
    for page_number in xrange(1, max_pages + 1):
        extract_app_ids(get_apps_page(page_number), apps)
    save_app_ids(apps)
