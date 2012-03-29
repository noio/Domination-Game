#!/usr/bin/env python
""" Domination game engine for Reinforcement Learning research.

Contains functions for running a tournament between agents.

"""

### IMPORTS ###
# Python
import datetime
import os
import csv
import glob
import sys
import pickle
import zipfile
from collections import defaultdict
from optparse import OptionParser

# Local
import core
from utilities import *

### FUNCTIONS ###

def run_game(gamekwargs, load_blobs=True):
    """ Runs a single game. This function can be used by Pool.map 
    
        :param gamekwargs: A list of dictionaries that will be passed as
                           arguments to the Game() constructor
        :param load_blobs: Open a blob and pass it to the agent if there is a 
                           file with the same name as the agent + '_blob'
    """
    gamekwargs['red_init'] = gamekwargs.get('red_init',{})
    gamekwargs['blue_init'] = gamekwargs.get('blue_init',{})
    red_blob = None
    blue_blob = None
    if load_blobs:
        red_blob_path = os.path.splitext(gamekwargs['red'])[0] + '_blob'
        blue_blob_path = os.path.splitext(gamekwargs['blue'])[0] + '_blob'
        if os.path.exists(red_blob_path):
            red_blob = open(red_blob_path,'rb')
            gamekwargs['red_init']['blob'] = red_blob
        if os.path.exists(blue_blob_path):
            blue_blob = open(blue_blob_path,'rb')
            gamekwargs['blue_init']['blob'] = blue_blob
    # Run the actual game
    game = core.Game(**gamekwargs).run()
    # Close the blobs neatly
    if red_blob is not None:
        red_blob.close()
    if blue_blob is not None:
        blue_blob.close()
    print "Game between %s (%d-%d) %s done."%(game.red.fullname(), game.score_red, 
                                              game.score_blue, game.blue.fullname())
    return (game.stats, game.replay, game.log)
    
def run_games(gamekwargs, max_threads=2):
    """ Runs multiple games, using Pool.map if 
        multiprocessing can be imported.
        
        :param gamekwargs: A list of dictionaries of arguments to each Game().
    """
    try:
        from multiprocessing import Pool, cpu_count
        threads = min(max_threads, cpu_count())
        print "Using %d threads to run games." % (threads)
        pool = Pool(threads)
        games = pool.map(run_game, gamekwargs)
    except ImportError:
        print "No multithreading available, running on single CPU."
        games = map(run_game, gamekwargs)

    return games
    
def full(agents=[], settings=core.Settings(), field=core.FieldGenerator(), 
        repeats=2, swap=True, folder=None, output_folder=None, draw_margin=0.05,
        max_threads=2, save_all=True):
    """ Runs a full tournament between given agents. 
    """
    if folder is not None:
        agents = glob.glob(os.path.join(folder,'*.py'))
        if output_folder is None:
            output_folder = folder
    # Generate the list of games to be played
    pairs = list(all_pairs(agents))
    pairs = pairs * repeats
    if swap:
        pairs = pairs + [(b,r) for (r,b) in pairs]
    # Generate the arguments to Game() for each match
    def _m((red, blue)):
        return {'red':  red,
                'blue': blue,
                'settings': settings,
                'field': field,
                'record':   True,
                'verbose':  False,
                'rendered': False}
    gamekwargs = map(_m, pairs)
    print "Running %d games." % (len(gamekwargs))
    gameinfo = run_games(gamekwargs, max_threads=max_threads)
    
    if os.path.exists(output_folder):
        print "WARNING: Output directory exists; overwriting results"
    else:
        os.makedirs(output_folder)
    # Write stats to a CSV
    fieldnames = ('red_file', 'blue_file', 'score', 'score_red', 'score_blue', 'steps', 'ammo_red', 'ammo_blue')
    now = datetime.datetime.now()
    fn = os.path.join(output_folder,'%s'%now.strftime("%Y%m%d-%H%M"))
    csvf = csv.DictWriter(open(fn+'_games.csv','w'), fieldnames, extrasaction='ignore')
    csvf.writerow(dict(zip(fieldnames, fieldnames)))
    # Create a zip with the replays
    if save_all:
        repzip = zipfile.ZipFile(fn+'_replays.zip','w')
        logzip = zipfile.ZipFile(fn+'_logs.zip','w')
    # Remove the common prefix from agent filenames
    prefix = os.path.commonprefix(agents).rfind('/') + 1
    games = []
    for ((r,b), (stats, replay, log)) in zip(pairs, gameinfo):
        r = r[prefix:]
        b = b[prefix:]
        games.append((r, b, stats, replay, log))
    
    for i, (r, b, stats, replay, log) in enumerate(games):
        # Write to the csv file
        s = stats.__dict__
        s.update([('red_file',r),('blue_file',b)])
        csvf.writerow(s)
        # Write a replay
        r = os.path.splitext(os.path.basename(r))[0]
        b = os.path.splitext(os.path.basename(b))[0]
        if save_all:
            repzip.writestr('replay_%04d_%s_vs_%s.pickle'%(i, r, b), pickle.dumps(replay, pickle.HIGHEST_PROTOCOL))
            logzip.writestr('log_%04d_%s_vs_%s.txt'%(i,r,b), log.truncated(kbs=32))
        
    if save_all:
        repzip.close()
        logzip.close()
        
    # Write summary
    by_match = defaultdict(lambda: defaultdict(int))
    by_team = defaultdict(int)
    # Compile scores by color/team/matchup
    for (r, b, stats, _, _) in games:
        if abs(stats.score - 0.5) < draw_margin:
            points_red, points_blue = (1, 1)
        elif stats.score > 0.5:
            points_red, points_blue = (2, 0)
        else:
            points_red, points_blue = (0, 2)
        by_match[r][b] += points_red
        by_match[b][r] += points_blue
        by_team[r] += points_red
        by_team[b] += points_blue
    
    order = sorted(by_team.keys(), key=lambda t: by_team[t], reverse=True)
    
    fieldnames = [ 'team', 'total'] + order
    sf = csv.DictWriter(open(fn+'_summary.csv','w'), fieldnames)
    sf.writerow(dict(zip(fieldnames, fieldnames)))
    
    for team in order:
        row = {'team':team, 'total':by_team[team]}
        row.update(by_match[team])
        sf.writerow(row)

### COMMAND LINE INTERFACE ###

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--folder", help="Folder that agents reside in [default: %default]", default="agents")    
    parser.add_option("-r", "--repeats", help="Number of times to repeat each game [default: %default]", default=2)
    parser.add_option("-t", "--threads", help="How many threads to use [default: %default]", default=2)    
    parser.add_option("-x", "--noswap", help="Disable swapping of red/blue teams", action="store_false", dest='swap', default=True)
    parser.add_option("-c", "--compact", help="Disable saving of replays/logs to save space", action="store_true", dest='compact', default=False)
    parser.add_option("-s", "--settings", help="Python dict of settings as a string [default: %default]", default="{}")
    (options, args) = parser.parse_args()
    if len(sys.argv) < 2:
        parser.print_help()
        print
        quit()
    settings = core.Settings(**eval(options.settings))
    print settings
    full(folder=options.folder, settings=settings, 
         repeats=int(options.repeats), swap=options.swap,
         max_threads=int(options.threads), save_all=not options.compact)