from __future__ import print_function, division

import logging

from app.steam.models import Game, Tag
from operator import itemgetter, attrgetter
from random import sample

MAX_GAMES = 50

def jaccard_sim(tag_set1, tag_set2):
    return len(tag_set1 & tag_set2) / len(tag_set1 | tag_set2)

def do_jaccard(game_name):
    games = Game.find_by_name(game_name)
    if len(games) > 0:
        # Let's just look at the first one for now
        game = games[0]
        tag_set = set(game.tags.keys())
        tags = sorted(map(Tag.get, tag_set), key=attrgetter("weight"), reverse=True)

        if len(tags[0].app_ids) > MAX_GAMES:
            # Because we can't pull down the entire database, and we're still tweaking caching, we
            # have to restrict ourselves to what we got, which is the first MAX_GAMES games from the
            # most relevant tag, ranked by absolute position in the total ranking of Steam games.
            to_get = set(sample(tags[0].app_ids, MAX_GAMES))
            games = sorted(Game.get(to_get).values(), key=attrgetter("score_rank"), reverse=True)
            return games
        else:
            to_get = set()
            for tag in tags:
                if len(tag.app_ids) + len(to_get) > MAX_GAMES:
                    # Much like above, if concatenating the app_ids for this tag would bring us over
                    # the MAX_GAMES element limit, we have to choose the games from this tag that we
                    # want to use. In this case, we don't really have a choice since we don't know
                    # what the actual games are, so we just choose randomly.
                    to_get.update(sample(tag.app_ids, MAX_GAMES - len(to_get)))
                else:
                    to_get.update(tag.app_ids)

            games = sorted(Game.get(to_get).values(), key=attrgetter("score_rank", reverse=True))
            scores = [(jaccard_sim(tag_set, set(g.tags.keys())), g) for g in games]
            # Because we sorted games by their score_rank, and this is a stable sort, the games that
            # have an equal jaccard metric will then be sorted by their score_rank.
            scores.sort(reverse=True, key=itemgetter(0))
            return map(itemgetter(1), scores)
    else:
        logging.error("Game was None for " + game_name)
