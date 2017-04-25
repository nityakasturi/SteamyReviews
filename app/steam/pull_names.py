import numpy as np
import json

def matrix_to_names():
    arr = np.load('data/compressed_matrix.npy')
    app_ids = arr[:,0].astype(int)
    with open('data/app_ids.json') as f:
        app_id_to_name = json.load(f)
    names = []
    for game in app_id_to_name:
        if int(game['app_id']) in app_ids:
            names.append(game['name'])
    with open('data/app_names.json', 'w') as f:
        print json.dumps(names)
        json.dump(names, f)

if __name__ == '__main__':
    matrix_to_names()
