from bs4 import BeautifulSoup, Tag

import requests
import numpy as np
import pickle
import json
import time
import os
import re

def get_descriptions():
    arr = np.load('data/compressed_matrix.npy')
    app_ids = arr[:,0].astype(int)

    descriptions = {}
    i = 0

    if os.path.isfile('data/descriptions.pkl'):
        pkl_file = open('data/descriptions.pkl', 'rb')
        descriptions = pickle.load(pkl_file)
        pkl_file.close()
        app_ids = [376310, 377330]

    while i < len(app_ids):
        print app_ids[i]
        url = "http://store.steampowered.com/api/appdetails?appids=" + str(app_ids[i])
        r  = requests.get(url)
        data = r.text
        json_data = json.loads(data)
        # print json_data[str(app_id)]['data']
        if json_data is None:
            time.sleep(5)
            attempts += 1
            if attempts == 5:
                cookies = {'birthtime':'28801'}
                url = "http://store.steampowered.com/app/" + str(app_ids[i]) + "/"
                r  = requests.get(url, cookies=cookies)
                if r.url == url:
                    data = r.text
                    soup = BeautifulSoup(data)
                    text = soup.find('div', attrs={'id':'game_area_description'})
                    descriptions[app_ids[i]] = text.get_text()[17:]
                    print text.get_text()[17:]
                    attempts = 0
                    i = i + 1
                else:
                    print "ERROR - does not exist or age check not working"
            print json_data
        elif json_data[str(app_ids[i])]['success'] == True:
            soup = BeautifulSoup(json_data[str(app_ids[i])]['data']['about_the_game'], 'html.parser')
            if not re.search('[a-zA-Z]', soup.get_text()):
                soup = BeautifulSoup(json_data[str(app_ids[i])]['data']['short_description'], 'html.parser')
            descriptions[app_ids[i]] = soup.get_text()
            print soup.get_text()
            i = i + 1
            attempts = 0
        else:
            print json_data
            i = i + 1
            attempts = 0

    pkl_file = open('data/descriptions.pkl', 'wb')
    pickle.dump(descriptions, pkl_file)
    pkl_file.close()

if __name__ == "__main__":
    get_descriptions()
