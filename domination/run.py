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
try:
    import cPickle as pickle
except ImportError:
    import pickle
import zipfile
import math
from optparse import OptionParser

# Local
import core
from utilities import *

# Shortcuts
pi = math.pi

### CLASSES ###

class Scenario(object):
    """ A scenario is used to run multiple games under the same conditions. """
    
    #: The settings with which these games will be played
    SETTINGS     = core.Settings()
    #: The field that these games will be played on
    FIELD        = core.FieldGenerator().generate() 
    REPEATS      = 2     #: How many times to repeat each game
    SWAP_TEAMS   = False #: Repeat each run with blue/red swapped
            
    def setup(self):
        pass
        
    def before_each(self):
        pass
        
    def after_each(self, game):
        """ Function that is run after each game.
            :param game: The previous game
        """
        pass
    
        
    """ You shouldn't have to override any
        of the methods below, but you may.
    """ 
    def _single(self, red, blue, rendered=False):
        """ Runs a single game, returns results, called repeatedly
            by :meth:`Scenario._multi`.
        """
        self.before_each()
        # Open blobs for reading if we can find 'em
        red_blob = os.path.splitext(red)[0] + '_blob'
        blue_blob = os.path.splitext(blue)[0] + '_blob'
        red_init = {'blob': open(red_blob,'r')} if os.path.exists(red_blob) else {}
        blue_init = {'blob': open(blue_blob,'r')} if os.path.exists(blue_blob) else {}
        # Run the game
        game = core.Game(red, blue, 
                    red_init=red_init, blue_init=blue_init,
                    field=self.FIELD, settings=self.SETTINGS,
                    record=True, verbose=False, rendered=False)
        if rendered:
            game.add_renderer()
        game.run()
        # Close the blobs
        if 'blob' in red_init:
            red_init['blob'].close()
        if 'blob' in blue_init:
            blue_init['blob'].close()
        self.after_each(game)
        return (game.stats, game.replay)
        
        
    def _multi(self, teams, output_folder=None, rendered=False):
        """ Runs multiple games, given as  a list of
            (red, red_init, blue, blue_init) tuples. 
        """
        self.setup()
        # Manipulate the playlist a bit
        teams = teams * self.REPEATS
        if self.SWAP_TEAMS:
            teams = teams + [(b, r) for (r, b) in teams]
        # Run the games
        stats   = []
        replays = []
        for i, (red, blue) in enumerate(teams):
            (stat, replay) = self._single(red, blue, rendered=rendered)
            print "======= Game %d/%d done. =======" % (i+1, len(teams))
            print stat
            stats.append(stat)
            replays.append(replay)
            
        if output_folder is not None:
            if os.path.exists(output_folder):
                print "WARNING: Output directory exists; overwriting results"
            else:
                os.makedirs(output_folder)
            # Write stats to a CSV
            fieldnames = ('red', 'blue', 'score', 'score_red', 'score_blue', 'steps', 'ammo_red', 'ammo_blue')
            now = datetime.datetime.now()
            fn = os.path.join(output_folder,'%s'%now.strftime("%Y%m%d-%H%M"))
            csvf = csv.DictWriter(open(fn+'_games.csv','w'), fieldnames, extrasaction='ignore')
            csvf.writerow(dict(zip(fieldnames, fieldnames)))
            # Create a zip with the replays
            zipf = zipfile.ZipFile(fn+'_replays.zip','w')
            
            for i, ((r, b), stats, replay) in enumerate(zip(teams, stats, replays)):
                # Write to the csv file
                s = stats.__dict__
                s.update([('red',r),('blue',b)])
                csvf.writerow(s)
                # Write a replay
                r = os.path.splitext(os.path.basename(r))[0]
                b = os.path.splitext(os.path.basename(b))[0]
                zipf.writestr('replay_%04d_%s_vs_%s.pickle'%(i, r, b), pickle.dumps(replay))
                
            zipf.close()
    
    @classmethod
    def test(cls, red, blue):
        scen = cls()
        scen.REPEATS = 1
        scen.SWAP_TEAMS = False
        scen._multi([(red, blue)], rendered=True)
    
    @classmethod
    def one_on_one(cls, red, blue, output_folder=None):
        scen = cls()
        scen._multi([red, blue], output_folder=output_folder)
        
    @classmethod
    def tournament(cls, agents=None, from_folder=None, output_folder=None):
        if from_folder is not None:
            agents = glob.glob(os.path.join(from_folder,'*.py'))
        pairs = list(all_pairs(agents))
        print pairs
        scen = cls()
        scen._multi(pairs, output_folder=output_folder)
        

        