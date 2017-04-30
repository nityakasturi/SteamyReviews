from __future__ import print_function

import json
import numpy as np

from app import app
from app.models import Game, Tag
from flask import request, render_template
from operator import itemgetter

DEFAULT_KWARGS = {
    "name": "Steamy Reviews",
    "netid": "bg379, hju3, nsk43, pmc85",
}
MAX_RANK_RESULTS = 27

@app.route("/", methods=["GET"])
def search():
    app_id = request.args.get("app_id", "").strip() or None
    query = request.args.get("search", "").strip() or None
    user_vector_toggle = request.args.get("user_vector", "") or "off"
    print(user_vector_toggle)
    if app_id is not None and app_id.isdigit():
        game = Game.get(int(app_id))
        if game is not None:
            return render_ranking_page(game)
        else:
            return render_template("search.html",
                                   no_such_app_id=True,
                                   username=request.cookies.get("username"),
                                   user_vector_toggle=user_vector_toggle,
                                   **DEFAULT_KWARGS)
    elif query is not None and len(query) > 0:
        game = Game.find_by_name(query)
        if game is not None:
            return render_ranking_page(game)
        else:
            app.logger.info("No result for " + query.encode("ascii", "ignore"))
            didyoumean1, didyoumean2 = Game.correct_game_name(query, max_results=2)
            return render_template("search.html",
                                   didyoumean1=didyoumean1,
                                   didyoumean2=didyoumean2,
                                   query=query,
                                   username=request.cookies.get("username"),
                                   user_vector_toggle=user_vector_toggle,
                                   **DEFAULT_KWARGS)

    else:
        return render_template("search.html",
                               username=request.cookies.get("username"),
                               user_vector_toggle=user_vector_toggle,
                               **DEFAULT_KWARGS)

def render_ranking_page(game):
    username = request.cookies.get("username")

    user_vector_toggle = request.args.get("user_vector", "") or "off"
    if username is None and user_vector_toggle == "on":
        user_vector_toggle = "off"

    library_vector = None
    if ("library_vector" in request.cookies) and user_vector_toggle:
        library_vector = np.array(json.loads(request.cookies.get("library_vector")))
    app.logger.error("Getting ranking")
    ranking = do_cosine_sim(game, max_results=MAX_RANK_RESULTS, library_vector=library_vector)
    app.logger.info("Results for " + game.normalized_name + ": " + str(ranking))
    return render_template("search.html",
                           query_game=game,
                           ranking=ranking,
                           username=username,
                           user_vector_toggle=user_vector_toggle,
                           **DEFAULT_KWARGS)

def jaccard_sim(tag_set1, tag_set2):
    return len(tag_set1 & tag_set2) / len(tag_set1 | tag_set2)

def do_jaccard(query, max_results):
    tag_set = set(query.tags.keys())
    matching_app_ids = Tag.get_games_with_tags(tag_set)
    to_get = set()
    for games in matching_app_ids.values():
        to_get.update(games)
    to_get.remove(query.app_id)
    games = Game.get(to_get)
    scores = [(jaccard_sim(tag_set, set(g.tags.keys())), g.score_rank, g) for g in games.values()]
    # Magic trick: Python sorts tuples element-wise, so if the first value in a pair of tuples
    # is equal, it will sort by the next and so on. Since the score_rank is second element,
    # games with equal Jaccard will then be sorted by score_rank.
    scores.sort(reverse=True)
    scores = map(itemgetter(2), scores)
    if max_results is None:
        return scores
    else:
        return scores[:max_results]

def do_cosine_sim(query, max_results, library_vector):
    return query.get_ranking(library_vector)[:max_results]
