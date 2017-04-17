from __future__ import print_function

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
            print("Results for", query, ":", results)
            data = map(lambda g: g.steam_url, results)
        else:
            data = []
            print("No results for", query)
	return render_template('search.html', name=project_name, netid=net_id, output_message=output_message, data=data)



