#!/usr/bin/python
import sys
import os

sys.stdout = sys.stderr
root = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, root)

activate_this = '/home/pmc85/envs/SteamyReviews/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

# Only for use on Zissou, otherwise set vars trough actual environment
env_file = '/home/pmc85/envs/SteamyReviews/env_vars'
with open(env_file) as env:
    for line in env:
        line = line.strip()
        i = line.find("=")
        os.environ[line[:i]] = line[i+1:]

print os.environ['PATH']
from app import app
