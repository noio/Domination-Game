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
from collections import defaultdict

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
    GENERATOR   = core.FieldGenerator() #: Will generate FIELD before each game if defined
    FIELD       = None   #: Will play on this field if GENERATOR is None
    REPEATS     = 2      #: How many times to repeat each game
    SWAP_TEAMS  = True   #: Repeat each run with blue/red swapped
    DRAW_MARGIN = 0.05
            
    def setup(self):
        """ Function is called once before any games 
        """
        pass
        
    def before_each(self):
        """ Function that is run before each game.
            Use it to regenerate the map, for example.
        """
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
        if self.GENERATOR is not None:
            self.FIELD = self.GENERATOR.generate()
        self.before_each()
        # Open blobs for reading if we can find 'em
        red_blob = os.path.splitext(red)[0] + '_blob'
        blue_blob = os.path.splitext(blue)[0] + '_blob'
        red_init = {'blob': open(red_blob,'rb')} if os.path.exists(red_blob) else {}
        blue_init = {'blob': open(blue_blob,'rb')} if os.path.exists(blue_blob) else {}
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
        return game
        
        
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
        gameinfo = []
        # print '\n'.join("%r vs. %r"%(r,b) for (r, b) in teams)
        for i, (red, blue) in enumerate(teams):
            game = self._single(red, blue, rendered=rendered)
            print "======= Game %d/%d done. =======" % (i+1, len(teams))
            print game.stats
            gameinfo.append((red, blue, game.stats, game.replay, game.log))
            
        if output_folder is not None:
            self._write(gameinfo, output_folder)
            
    def _write(self, gameinfo, output_folder, include_replays=True):
        """ Write a csv with all game results, all the replays in a zip and
            a textfile with a summary to the output_folder
        """
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
        zipf = zipfile.ZipFile(fn+'_replays.zip','w')
        logs = zipfile.ZipFile(fn+'_logs.zip','w')
            
        for i, (r, b, stats, replay, log) in enumerate(gameinfo):
            # Write to the csv file
            s = stats.__dict__
            s.update([('red_file',r),('blue_file',b)])
            csvf.writerow(s)
            # Write a replay
            r = os.path.splitext(os.path.basename(r))[0]
            b = os.path.splitext(os.path.basename(b))[0]
            zipf.writestr('replay_%04d_%s_vs_%s.pickle'%(i, r, b), pickle.dumps(replay, pickle.HIGHEST_PROTOCOL))
            logs.writestr('log_%04d_%s_vs_%s.txt'%(i,r,b), log.truncated(kbs=1))
        
        zipf.close()
        logs.close()
        
        # Write summary
        sf = open(fn+'_summary.md','w')
        sf.write('In total, %d games were played.\n\n' % len(gameinfo))
        by_color = defaultdict(lambda: [0, 0])
        by_match = defaultdict(lambda: [0, 0])
        by_team = defaultdict(lambda: 0)
        # Compile scores by color/team/matchup
        for (r, b, stats, _, _) in gameinfo:
            if abs(stats.score - 0.5) < self.DRAW_MARGIN:
                points_red, points_blue = (1, 1)
            elif stats.score > 0.5:
                points_red, points_blue = (2, 0)
            else:
                points_red, points_blue = (0, 2)
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
        
    
    @classmethod
    def test(cls, red, blue):
        """ Test this scenario, this will run a single
            game and render it, so you can verify the
            FIELD and SETTINGS.
            
            :param red:  Path to red agent
            :param blue: Path to blue agent
        """
        scen = cls()
        scen.REPEATS = 1
        scen.SWAP_TEAMS = False
        scen._multi([(red, blue)], rendered=True)
    
    @classmethod
    def one_on_one(cls, red, blue, output_folder=None):
        """ Runs the set amount of REPEATS and SWAP_TEAMS if
            desired, between two given agents.
            
            :param output_folder: Folder in which results will be stored
        """
        scen = cls()
        scen._multi([(red, blue)], output_folder=output_folder)
        
    @classmethod
    def tournament(cls, folder=None, agents=None, output_folder=None):
        """ Runs a full tournament between the agents specified,
            respecting the REPEATS and SWAP_TEAMS settings.
        
            :param agents:        A list of paths to agents
            :param folder:        A folder that contains all agents, overrides the agents parameter.
            :param output_folder: Folder in which results will be stored.
        """
        if folder is not None:
            agents = glob.glob(os.path.join(folder,'*.py'))
            if output_folder is None:
                output_folder = folder
        pairs = list(all_pairs(agents))
        scen = cls()
        scen._multi(pairs, output_folder=output_folder)
        

### HELPER FUNCTIONS ###

def markdown_table(body, header=None):
    """ Generate a MultiMarkdown text table.
        :param body:    The body as a list-of-lists
        :param header:  The header to print
    """
    s = ""
    
    def makerow(row):
        rowstrs = [str(cell).ljust(maxlen[i]) for i,cell in enumerate(row)]
        return '| ' + ' | '.join(rowstrs) + ' |\n'
    
    if header:
        body = [header] + body
    maxlen = [max(len(str(cell)) for cell in col) for col in zip(*body)]
    if header:
        s += makerow(body[0])
        s += '|'+'|'.join('-'*(m+2) for m in maxlen)+'|\n'
        body = body[1:]
    for row in body:
        s += makerow(row)
    return s
    

        
if __name__ == '__main__':
    Scenario.one_on_one(red=core.DEFAULT_AGENT_FILE, blue=core.DEFAULT_AGENT_FILE, output_folder='_tmp')

        
