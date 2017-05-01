from __future__ import print_function

import json
import numpy as np

from app.models import Game
from app.models.tag import compute_reverse_index
from app.utils import data_file

if __name__ == '__main__':
    games = list(Game.get_all())
    reverse_index = compute_reverse_index(games)
    doc_tag_matrix = np.zeros((len(games), len(reverse_index) + 1), dtype=np.int)
    app_ids = sorted([game.app_id for game in games])
    tag_ids = sorted(reverse_index.keys())
    doc_tag_matrix[:, 0] = np.array(app_ids)

    for app_index in xrange(len(games)):
        for tag_index in xrange(len(reverse_index)):
            if app_ids[app_index] in reverse_index[tag_ids[tag_index]]:
                doc_tag_matrix[app_index, tag_index + 1] = 1

    with open(data_file("doc_tag_matrix.npy"), "wb") as f:
        np.save(f, doc_tag_matrix)
