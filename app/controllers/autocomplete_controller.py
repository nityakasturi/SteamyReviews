from __future__ import print_function

import logging
import urllib
import json

from app import app
from app.models import Game
from flask import render_template

@app.route("/dynamic/js/autocomplete.js")
def autocomplete():
    # Assign a member to the function itself (waaaaaaaatt???) because that template is essentially
    # static, but might change for different versions of the app, so it's not worth hard-coding
    # anywhere, but in development, it's still nice to see changes reflected, so it bypasses the
    # cache.
    if app.config["DEBUG"] or not hasattr(autocomplete, "cache"):
        app_id_to_name = [{"data": game.app_id, "value": game.name} for game in Game.get_all()]
        autocomplete.cache = render_template("autocomplete.js",
                                             app_id_to_name=json.dumps(app_id_to_name))
    return autocomplete.cache
