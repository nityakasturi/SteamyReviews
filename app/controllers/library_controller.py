from __future__ import print_function

import requests
import json
import numpy as np

from flask import request, render_template, session, redirect, make_response
from app import app
from app.models import Game

STEAM_API_KEY = app.config['STEAM_API_KEY']
SECRET_KEY = app.config['SECRET_KEY']

@app.route("/steam/login", methods=['GET', 'POST'])
def login():
    username = request.form['username']
    redirect_to_home = redirect("/")
    response = make_response(redirect_to_home)
    if username != "":
        params = {
            'key': STEAM_API_KEY,
            'vanityurl': username
        }
        r = requests.get("http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/", params)
        success = int(r.json()['response']['success'])
        if success == 1:
            steamid = r.json()['response']['steamid']
            response.set_cookie("steam_ID", value=steamid)
            del params['vanityurl']
            params['steamids'] = steamid
            r3 = requests.get("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
                              params)
            if 200 <= r3.status_code < 300:
                response.set_cookie("username",
                                    value=r3.json()['response']['players'][0]['personaname'])
                del params["steamids"]
                params["steamid"] = steamid
                params["format"] = "json"
                params["include_played_free_games"] = "1"
                r2 = requests.get("http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
                                  params)
                if 'games' not in r2.json()['response']:
                    return render_template("search.html",
                                           username=request.cookies.get("username"),
                                           invalid_login=True)
                games = r2.json()['response']['games']
                game_list = [int(game['appid']) for game in games]
                hours_played = [int(game['playtime_forever']) for game in games]
                response.set_cookie("game_list", value=json.dumps(game_list))
                library_vector = Game.compute_library_vector(game_list, hours_played)
                response.set_cookie("library_vector", value=json.dumps(library_vector.tolist()))
            else:
                pass #???
        else:
            return render_template("search.html",
                                   username=request.cookies.get("username"),
                                   invalid_login=True)
    elif request.cookies.get('username'):
        del session["steam_ID"]
        del session["library_vector"]
        response.set_cookie("steam_id", "", max_age=0)
        response.set_cookie("library_vector", "", max_age=0)
    return response

