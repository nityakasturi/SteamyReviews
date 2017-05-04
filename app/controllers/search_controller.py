from __future__ import print_function

import json
import numpy as np

from app import app
from app.models import Game, Tag
from flask import request, render_template, g
from operator import itemgetter

DEFAULT_KWARGS = {
    "name": "Steamy Reviews",
    "netid": "bg379, hju3, nsk43, pmc85",
}
MAX_RANK_RESULTS = 27

@app.before_request
def parse_cookies():
    g.user_vector_toggle = request.args.get("user_vector", "") or "off"
    g.username = request.cookies.get("username")
    if g.username is None:
        g.user_vector_toggle = "off"

    g.library_vector = None
    g.game_list = None
    if g.username is not None:
        if "library_vector" in request.cookies:
            g.library_vector = np.array(json.loads(request.cookies.get("library_vector")))
        if "game_list" in request.cookies:
            g.game_list = set(json.loads(request.cookies.get("game_list")))
            if len(g.game_list) == 0:
                g.game_list = None

@app.route("/", methods=["GET"])
def search():
    app_id = request.args.get("app_id", "").strip() or None
    query = request.args.get("search", "").strip() or None
    only_library_vector = request.args.get("only_library_vector", "off") == "on"
    removed_features = request.args.get("removed_features", "").decode('base64').split(",") or []
    removed_features = Game.get_feature_indices(removed_features)

    if only_library_vector and g.library_vector is not None and g.game_list is not None:
        return render_ranking_page(None, True, removed_features=removed_features)
    elif app_id is not None and app_id.isdigit():
        game = Game.get(int(app_id))
        if game is not None:
            return render_ranking_page(game, False, removed_features=removed_features)
        else:
            return render_search_template(no_such_app_id=True)
    elif query is not None and len(query) > 0:
        game = Game.find_by_name(query)
        if game is not None:
            return render_ranking_page(game, False, removed_features=removed_features)
        else:
            app.logger.info("No result for " + query.encode("ascii", "ignore"))
            didyoumean1, didyoumean2 = Game.correct_game_name(query, max_results=2)
            return render_search_template(didyoumean1=didyoumean1,
                                          didyoumean2=didyoumean2,
                                          query=query)

    else:
        return render_search_template()

def render_ranking_page(game, only_library_vector, removed_features=None):
    if only_library_vector:
        app.logger.info("Getting ranking for library vector query.")
        ranking = [rank
                   for rank in Game.compute_ranking_for_vector(g.library_vector, removed_features)
                   if rank[1].app_id not in g.game_list][:MAX_RANK_RESULTS]
        features, feature_names = Game.get_vector_best_features(g.library_vector, True)
        return render_search_template(ranking=ranking,
                                      user_ranking=None,
                                      library_features=features,
                                      library_feature_names=feature_names,
                                      library_vector=g.library_vector)
    else:
        app.logger.info("Getting ranking")
        base_ranking = do_cosine_sim(game, library_vector=None, removed_features=removed_features)
        app.logger.debug("Results for " + game.normalized_name + ": " + str(base_ranking))

        user_ranking = None
        offset_vector = None
        if g.library_vector is not None:
            app.logger.info("User is logged in. Also getting vector ranking.")
            # I know we end up computing this twice, but that's the problem with running the query
            # with one vector and displaying another
            offset_vector = json.dumps(game.offset_vector(g.library_vector,
                                                          only_best_features=True).tolist())
            user_ranking = do_cosine_sim(game, g.library_vector, removed_features)
            app.logger.debug("Results for " + game.normalized_name + ": " + str(user_ranking))

        return render_search_template(query_game=game,
                                      ranking=base_ranking,
                                      user_ranking=user_ranking,
                                      offset_vector=offset_vector)

def render_search_template(**kwargs):
    for k in DEFAULT_KWARGS:
        if k not in kwargs:
            kwargs[k] = DEFAULT_KWARGS[k]
    return render_template("search.html",
                           username=g.username,
                           user_vector_toggle=g.user_vector_toggle,
                           **kwargs)

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

def do_cosine_sim(query, library_vector, removed_features, max_results=MAX_RANK_RESULTS):
    return [rank
            for rank in query.get_ranking(library_vector, removed_features)
            if g.game_list is None or rank[1].app_id not in g.game_list][:max_results]
