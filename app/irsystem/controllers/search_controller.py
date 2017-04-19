from __future__ import print_function

import app
import logging
import urllib

from . import irsystem, request, render_template
from app.irsystem.models.search import do_jaccard
from app.steam.models import Game

DEFAULT_KWARGS = {
    "name": "Steamy Reviews",
    "netid": "bg379, hju3, nsk43, pmc85",
}

@irsystem.route("/", methods=["GET"])
def search():
    query = request.args.get("search")
    if query is not None and len(query) > 0:
        results = Game.find_by_name(query)
        if results is None or len(results) == 0:
            game = Game.correct_game_name(query)
            logging.error("No results for " + query.encode("ascii", "ignore"))
            return render_template("search.html",
                                   didyoumean=game.name,
                                   query=query,
                                   **DEFAULT_KWARGS)
        else:
            game = results[0]
            ranking = do_jaccard(game)
            logging.error("Results for " + game.normalized_name + ": " + str(ranking))
            return render_template("search.html", query=query, ranking=ranking, **DEFAULT_KWARGS)
    else:
        logging.error("/GET")
        return render_template("search.html", **DEFAULT_KWARGS)
