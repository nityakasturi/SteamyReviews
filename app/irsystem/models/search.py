from __future__ import print_function, division

import logging

from operator import itemgetter

from app.steam.models import Game, Tag

def jaccard_sim(tag_set1, tag_set2):
    return len(tag_set1 & tag_set2) / len(tag_set1 | tag_set2)

def do_jaccard(game_name):
    game = Game.find_by_name(game_name)
    if game is not None:
        tag_set = set(game.tags.keys())
        game_ids = Tag.get_games_with_tags(tag_set)
        if len(game_ids) > 0:
            matching_games = Game.get(game_ids)
            scores = [(jaccard_sim(tag_set, set(g.tags.keys())), g) for g in matching_games]
            scores.sort(reverse=True, key=itemgetter(0))
            return scores
        else:
            logging.error("game_ids was empty")
    else:
        logging.error("Game was None for " + game_name)
