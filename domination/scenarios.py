#!/usr/bin/env python
""" Domination game engine for Reinforcement Learning research.

Contains functions for running multiple games and tournaments.

"""

### IMPORTS ###
# Python
import datetime
import sys
import os
import csv
import glob
import cPickle as pickle
import zipfile
import math
import hashlib
import copy
import uuid
import shutil
from collections import defaultdict

# Local
import core
from utilities import *

# Shortcuts
pi = math.pi

### CONSTANTS ###
SCORING_LINEAR = 'linear'
SCORING_CONSTANT = 'constant'


### FUNCTIONS ###

def callfunc(tup):
    """ Function to ensure compatibility with Pool.map
    """
    (ob, fun, args, kwds) = tup
    return getattr(ob, fun)(*args, **kwds)

### CLASSES ###

class MatchInfo(object):
    """ An instance of this object is passed to agents to let them know
        that they are participating in a match consisting of multiple games,
        and which game they are currently in.
    """
    
    def __init__(self, num_games, current, match_id, score_weight):
        """ Constructor for MatchInfo 
        
            :param num_games:    The total number of games in this match
            :param current:      The current game with 1 being the first game.
            :param match_id:     A unique id of the opponent the agent is playing against.
            :param score_weight: How much weight is assigned to the score of the current match.
        """
        self.num_games    = num_games
        self.current      = current
        self.match_id     = match_id
        self.score_weight = score_weight
        

class Scenario(object):
    """ A scenario is used to run multiple games under the same conditions. """
    
    #: The settings with which these games will be played
    SETTINGS     = core.Settings()
    #: The field that these games will be played on
    GENERATOR         = core.FieldGenerator() #: Will generate FIELD before each game if defined
    FIELD             = None   #: Will play on this field if GENERATOR is None
    REPEATS           = 4      #: How many times to repeat each game
    SWAP_TEAMS        = True   #: Repeat each run with blue/red swapped
    DRAW_MARGIN       = 0.05
    SCORING           = SCORING_LINEAR

    MULTITHREADING = True
            
    def setup(self):
        """ Function is called once before any games 
        """
        pass
        
    def before_game(self):
        """ Function that is run before each game.
            Use it to regenerate the map, for example.
        """
        pass
        
    def after_game(self, game):
        """ Function that is run after each game.
            
            :param game: The previous game
        """
        pass
    
        
    """ You shouldn't have to override any
        of the methods below, but you may.
    """ 
    def _single(self, red, blue, matchinfo=None, rendered=False, verbose=False):
        """ Runs a single game, returns results, called repeatedly
            by :meth:`Scenario._multi`.
        """
        if self.GENERATOR is not None:
            self.FIELD = self.GENERATOR.generate()
        self.before_game()
        # Open blobs for reading if we can find 'em
        red_blob = os.path.splitext(red)[0] + '_blob'
        blue_blob = os.path.splitext(blue)[0] + '_blob'
        # Build the initializer arguments
        red_init = {}
        blue_init = {}
        if matchinfo is not None:
            red_init['matchinfo'] = matchinfo
            blue_init['matchinfo'] = matchinfo
        if os.path.exists(red_blob):
            red_init['blob'] = open(red_blob,'rb')
        if os.path.exists(blue_blob):
            blue_init['blob'] = open(blue_blob,'rb')
        
        # Run the game
        game = core.Game(red, blue, 
                    red_init=red_init, blue_init=blue_init,
                    field=self.FIELD, settings=self.SETTINGS,
                    record=True, verbose=verbose, rendered=False)
        if rendered:
            game.add_renderer()
        game.run()
        # Close the blobs
        if 'blob' in red_init:
            red_init['blob'].close()
        if 'blob' in blue_init:
            blue_init['blob'].close()
        self.after_game(game)
        print game.stats
        return (matchinfo, game.stats, game.replay, game.log)

    def _match(self, red, blue, output_folder, rendered, verbose):
        """ Runs a single match consisting of multiple games 
            Copies the agents to a temporary subfolder so that
            they can write to a unique blob.
        """
        # Create a folder for the agent copies
        uid = uuid.uuid4().hex[:8]
        path = os.path.join(output_folder,'matchups')
        rbase = os.path.splitext(os.path.basename(red))[0]
        bbase = os.path.splitext(os.path.basename(blue))[0]
        folder = os.path.join(path, '%s_vs_%s_%s' % (rbase, bbase, uid))
        os.makedirs(folder)

        # Copy the agents and blobs
        newred = os.path.join(folder, 'red_' + os.path.basename(red))
        newblue = os.path.join(folder, 'blue_' + os.path.basename(blue))
        shutil.copyfile(red, newred)
        shutil.copyfile(blue, newblue)
        red_blob = os.path.splitext(red)[0] + '_blob'
        blue_blob = os.path.splitext(blue)[0] + '_blob'
        if os.path.exists(red_blob):
            shutil.copyfile(red_blob, os.path.splitext(newred)[0] + '_blob')
        if os.path.exists(blue_blob):
            shutil.copyfile(blue_blob, os.path.splitext(newblue)[0] + '_blob')
        
        # Run the matches
        gameinfo = []
        for i in range(self.REPEATS):
            if self.SCORING == SCORING_CONSTANT or self.REPEATS == 1:
                score_weight = 1.0
            elif self.SCORING == SCORING_LINEAR:
                score_weight = 2.0 * i / (self.REPEATS - 1)
            matchinfo = MatchInfo(self.REPEATS, i, hash((red, blue)), score_weight)
            gameinfo.append((red, blue) + self._single(newred, newblue, matchinfo, rendered, verbose))
        return gameinfo
        
    def _multi(self, games, output_folder, rendered=False, verbose=False):
        """ Runs multiple matches, given as  a list of
            (red,  blue) tuples. 
        """
        self.setup()

        calls = [(self, '_match', (red, blue, output_folder, rendered, verbose), {}) 
                        for (red, blue) in games]
        # Run the games
        try:
            from multiprocessing import Pool, cpu_count
            threads = max(1, cpu_count() - 1)
            print "Using %d threads to run games." % (threads)
            pool = Pool(threads)
            gameinfos = pool.map(callfunc, calls)
        except ImportError:
            print "No multithreading available, running on single CPU."
            gameinfos = map(callfunc, calls)

        gameinfos = [gameinfo for l in gameinfos for gameinfo in l]
        if output_folder is not None:
            self._write(gameinfos, output_folder)
            
    def _write(self, gameinfo, output_folder, include_replays=True):
        """ Write a csv with all game results, all the replays in a zip and
            a textfile with a summary to the output_folder
        """
        # Find the prefix from the agent paths
        all_agents = set(a for g in gameinfo for a in (g[0], g[1]))
        prefix = os.path.commonprefix(all_agents).rfind('/') + 1
        
        # Configure the CSV
        fieldnames = ('red_file', 'blue_file', 'score_red', 'score_blue', 'score', 
                      'weight', 'points_red', 'points_blue', 'steps', 'ammo_red', 'ammo_blue')
        csvf = csv.DictWriter(open(os.path.join(output_folder, 'games.csv'),'w'), fieldnames, extrasaction='ignore')
        csvf.writerow(dict(zip(fieldnames, fieldnames)))

        # Open other files
        zipf = zipfile.ZipFile(os.path.join(output_folder, 'replays.zip'),'w', zipfile.ZIP_DEFLATED, True)
        logs = zipfile.ZipFile(os.path.join(output_folder, 'logs.zip'),'w', zipfile.ZIP_DEFLATED, True)
        sf = open(os.path.join(output_folder, 'summary.md'),'w')
        sf.write('In total, %d games were played.\n\n' % len(gameinfo))
        
        by_color = defaultdict(lambda: [0., 0.])
        by_match = defaultdict(lambda: [0., 0.])
        by_team = defaultdict(lambda: 0.)
        
        for i, (r, b, matchinfo, stats, replay, log) in enumerate(gameinfo):
            r = r[prefix:]
            b = b[prefix:]
            
            # Compute weighted score
            if abs(stats.score - 0.5) < self.DRAW_MARGIN:
                points_red, points_blue = (matchinfo.score_weight, matchinfo.score_weight)
            elif stats.score > 0.5:
                points_red, points_blue = (2 * matchinfo.score_weight, 0)
            else:
                points_red, points_blue = (0, 2 * matchinfo.score_weight)

            # Add scores to tables by color/team/matchup
            by_color[(r,b)][0] += points_red
            by_color[(r,b)][1] += points_blue
            if r < b:
                by_match[(r,b)][0] += points_red
                by_match[(r,b)][1] += points_blue
            else:
                by_match[(b,r)][0] += points_blue
                by_match[(b,r)][1] += points_red
            by_team[r] += points_red
            by_team[b] += points_blue
            
            # Write to the csv file
            s = copy.copy(stats.__dict__)
            s.update([('red_file',r), 
                      ('blue_file',b), 
                      ('weight', matchinfo.score_weight), 
                      ('points_red', points_red), 
                      ('points_blue', points_blue)])
            csvf.writerow(s)
            rbase = os.path.splitext(os.path.basename(r))[0]
            bbase = os.path.splitext(os.path.basename(b))[0]
            zipf.writestr('replay_%04d_%s_vs_%s.pickle'%(i, rbase, bbase), pickle.dumps(replay, pickle.HIGHEST_PROTOCOL))
            logs.writestr('log_%04d_%s_vs_%s.txt'%(i, rbase, bbase), log.truncated(kbs=32))
            
        
        # Put the matches into a matchup matrix (team a on left, team b on top)
        matrix = defaultdict(lambda: defaultdict(lambda: None))
        for (a, b), (points) in by_match.items():
            matrix[a][b] = points
        order = sorted(by_team.keys())
        table = [] #[[for _ in range(len(order)+1)] for _ in range(len(order))]
        for left in order[:-1]:
            table.append([left] + [matrix[left][top] for top in order[1:]])
        
        # Final ranking
        ranking = sorted(by_team.items(), key=lambda x: x[1], reverse=True)
        
        # Write to output
        sf.write(markdown_table([(r,b,pr,pb) for ((r,b),(pr,pb)) in by_color.items()], header=['Red','Blue','R','B']))
        sf.write('\n')
        sf.write(markdown_table(table, header=['']+order[1:]))
        sf.write('\n')
        sf.write(markdown_table(ranking, header=['Team','Points']))

        # Close all files
        zipf.close()
        logs.close()
        sf.close()
        
    
    @classmethod
    def test(cls, red, blue):
        """ Test this scenario, this will run a single
            game and render it, so you can verify the
            FIELD and SETTINGS.
            
            :param red:  Path to red agent
            :param blue: Path to blue agent
        """
        scen = cls()
        scen._single(red, blue, None, rendered=True, verbose=True)
    
    @classmethod
    def one_on_one(cls, output_folder, red, blue):
        """ Runs the set amount of REPEATS and SWAP_TEAMS if
            desired, between two given agents.
            
            :param output_folder: Folder in which results will be stored
        """
        cls.tournament(agents=[red, blue], output_folder=output_folder)
        
    @classmethod
    def tournament(cls, output_folder, folder=None, agents=None, rendered=False):
        """ Runs a full tournament between the agents specified,
            respecting the REPEATS and SWAP_TEAMS settings.
        
            :param agents:        A list of paths to agents
            :param folder:        A folder that contains all agents, overrides the agents parameter.
            :param output_folder: Folder in which results will be stored.
        """
        if os.path.exists(output_folder):
            print "WARNING: Output directory exists; overwriting results"
        else:
            os.makedirs(output_folder)
        
        if folder is not None:
            agents = glob.glob(os.path.join(folder,'*.py'))
            if output_folder is None:
                output_folder = folder
        matchups = list(all_pairs(agents))
        # Add swapped version
        if cls.SWAP_TEAMS:
            matchups += [(t1, t2) for (t2, t1) in matchups]
        
        scenario = cls()
        scenario._multi(matchups, output_folder=output_folder, rendered=rendered)
        

### HELPER FUNCTIONS ###

def markdown_table(body, header=None):
    """ Generate a MultiMarkdown text table.
        :param body:    The body as a list-of-lists
        :param header:  The header to print
    """
    s = ""
    def cellstr(cell):
        if type(cell) == float:
            return ("%.2f" % cell)
        if type(cell) in (list, tuple):
            return ', '.join(cellstr(e) for e in cell)
        return str(cell)
    
    def makerow(row):
        rowstrs = [cellstr(cell).rjust(maxlen[i]) for i,cell in enumerate(row)]
        return '| ' + ' | '.join(rowstrs) + ' |\n'
    
    if header:
        body = [header] + body
    maxlen = [max(len(cellstr(cell)) for cell in col) for col in zip(*body)]
    if header:
        s += makerow(body[0])
        s += '|'+'|'.join('-'*(m+2) for m in maxlen)+'|\n'
        body = body[1:]
    for row in body:
        s += makerow(row)
    return s
    

        
if __name__ == '__main__':
    now = datetime.datetime.now()
    folder = os.path.join('tournaments', now.strftime("%Y%m%d-%H%M"))
    Scenario.one_on_one(red='agent.py', blue='agent_adjustable.py', output_folder=folder)

    