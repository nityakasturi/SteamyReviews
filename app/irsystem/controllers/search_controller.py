from __future__ import print_function

import logging

import app

from . import *
from app.irsystem.models.search import do_jaccard
from app.irsystem.models.matrix import Matrix
from app.irsystem.models.redisconn import RedisConn as RedisConn
from app.irsystem.models.helpers import *
from app.irsystem.models.helpers import NumpyEncoder as NumpyEncoder

project_name = "Steamy Reviews"
net_id = ""

@irsystem.route('/', methods=['GET'])
def search():
	query = request.args.get('search')
	if not query:
		data = []
		output_message = ''
	else:
		output_message = "Your search: " + query
        results = do_jaccard(query)
        if results is not None:
            logging.error("Results for " + str(query) + ": " + str(results))
            data = map(lambda g: g.steam_url, results)
        else:
            data = []
            logging.error("No results for " + str(query))
	return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=data)
