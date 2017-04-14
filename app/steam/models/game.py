from __future__ import print_function, division

import requests
import json

from bs4 import BeautifulSoup

max_page = 750

class Game(object):
    @classmethod
    def from_table_row(cnstr, table_row):
        columns = map(lambda td: td.get_text(strip=True),
                      table_row.find_all("td"))
        return cnstr(app_id=columns[1],
                     name=columns[2],
                     recent_peak=int(columns[4].replace(",", "")),
                     max_peak=int(columns[5].replace(",", "")))

    def __init__(self, app_id, name, recent_peak, max_peak):
        self.app_id = app_id
        self.name = name
        self.recent_peak = recent_peak
        self.max_peak = max_peak

def get_app_ids_from_graph_page():
    """
    It turns out that this method is more reliable plus it gets us more data on
    current and popular games (and we don't have to do a big scan).
    """
    graph = requests.get("https://steamdb.info/graph/")
    soup = BeautifulSoup(graph.text, "lxml")
    table = soup.find("table", id="table-apps").find("tbody")
    return sorted(map(Game.from_table_row, table.find_all("tr", class_="app")),
                  key=lambda g: g.name)

def extract_app_ids(page, apps=dict()):
    """
    Get the page at https://steamdb.info/apps/page{page_number}/ which contains
    a list of game ids and titles. Use BeautifulSoup to extract the data into a
    more useable data structure.
    """
    if not 1 <= page_number <= max_pages:
        msg = "page_number must be between 1 and 750! Was %d"%page_number
        raise Exception(msg)
    url = "https://steamdb.info/apps/page%d/"%page_number
    res = requests.get(url)
    if not 200 <= res.status_code < 300:
        msg = "Invalid status code (%d) when fetching page %d"%(res.status_code,
                                                                page_number)
        raise Exception(msg)
    soup = BeautifulSoup(res.text, "lxml").find_all("tr", class_="app")
    for app in soup:
        i = app.find_all("i", class_="subinfo")
        if not (len(i) > 0 and i[0].text == "Game"):
            continue
        app_id = app["data-appid"]
        title = app.find_all("a", class_="b")[0].text
        apps[app_id] = title
    return apps

def get_all_pages(max_page=max_page):
    apps = dict()
    for page_number in xrange(1, max_pages + 1):
        extract_app_ids(page_number, apps)
    with open("app_ids.json", 'w') as f:
        json.dump(apps, f)

if __name__ == '__main__':
    games = get_app_ids_from_graph_page()
    with open("app_ids.json", 'w') as f:
        json.dump(games, f, default=lambda o: o.__dict__, indent=2)
