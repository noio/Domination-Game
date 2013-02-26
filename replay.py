#! /usr/bin/python

""" Run a replay file from the command line """

import pickle
import gzip
import sys
import glob
import os
import random

import domination

# This hack seems to be needed to make pickle find the core module
sys.path.append(os.path.split(__file__)[0])

def run_replay(path, rendered=True):
    openfile = gzip.open(path, 'rb') if path.endswith('.gz') else open(path, 'rb')
    g = domination.core.Game(replay=pickle.load(openfile), rendered=rendered).run()
    print g.stats


if __name__ == '__main__':
    if os.path.isdir(sys.argv[1]):
    	files = glob.glob(os.path.join(sys.argv[1], '*.pickle'))
    	# random.shuffle(files)
        for f in files:
            run_replay(f)
    else:
        rendered = '-s' not in sys.argv
        run_replay(sys.argv[1], rendered)

    