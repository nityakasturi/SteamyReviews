from __future__ import print_function

import logging

import app

from . import *
from app.irsystem.models.search import do_jaccard
from app.irsystem.models.matrix import Matrix
from app.irsystem.models.redisconn import RedisConn as RedisConn
from app.irsystem.models.helpers import *
from app.irsystem.models.helpers import NumpyEncoder as NumpyEncoder

PROJECT_NAME = "Steamy Reviews"
NET_IDS = "bg379, hju3, nsk43, pmc85"

@irsystem.route('/', methods=['GET'])
def search():
    query = request.args.get('search')
    if query is not None and len(query) > 0:
        output_message = "Your search: " + query
        results = do_jaccard(query)
        if results is not None:
            logging.error("Results for " + query.encode('ascii', 'ignore') + ": " + str(results))
            data = results
        else:
            data = []
            logging.error("No results for " + query.encode('ascii', 'ignore'))
    else:
        data = []
        output_message = ''
    return render_template('search.html',
                           name=PROJECT_NAME,
                           netid=NET_IDS,
                           output_message=output_message,
                           data=data)
