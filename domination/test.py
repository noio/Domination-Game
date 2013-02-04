#!/usr/bin/env python
""" Testing module for Domination game engine

Running this script will test if the domination game is
working properly. This includes saving fields and replays.
"""

### IMPORTS

# Python Imports
import os
import unittest
import shutil
import tempfile
import cPickle as pickle

# Local Imports
import core
import tournament
from utilities import *

### CONSTANTS

RANDOM_AGENT = """
class Agent(object):
    NAME = "randomagent"
    
    def __init__(self, *args, **kwargs):
        pass
    
    def observe(self, *args):
        pass
    
    def action(self):
        return (-pi + rand()*2*pi, 100, True)
    
    def debug(self, surface):
        pass
    
    def finalize(self, interrupted=False):
        pass
"""

SMALL_FIELD = """
w w w w w w w w w w w w w w w w w w w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w R _ _ _ _ _ C _ _ _ C _ _ _ _ _ B w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ w _ _ _ w _ _ _ _ _ _ w
w _ _ _ _ _ _ w _ _ _ w _ _ _ _ _ _ w
w _ _ _ _ _ _ w _ _ _ w _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w R _ _ _ _ _ _ _ A _ _ _ _ _ _ _ B w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w w w w w w w w w w w w w w w w w w w
"""

### CLASSES

class TestDominationGame(unittest.TestCase):
        
    def test_basic(self):
        core.Game(rendered=False, verbose=False).run()
        
    def test_team(self):
        tmpdir = '_tmp'
        if not os.path.exists(tmpdir):
            os.mkdir(tmpdir)
        agentpath = os.path.join(tmpdir,'agent.py')
        shutil.copy(core.DEFAULT_AGENT_FILE, agentpath)
    
        team = core.Team(agentpath)
        self.assertEqual(team.brain_string, open(agentpath).read())
    
        team = core.Team(open(agentpath))
        self.assertEqual(team.brain_string, open(agentpath).read())
    
        team = core.Team(open(agentpath,'r').read())
        self.assertEqual(team.brain_string, open(agentpath).read())
    
        team = core.Team(name='ya')
        teamb = core.Team()
        teamb.setname(team.fullname())
        self.assertEqual(team.fullname(), teamb.fullname())
        
    def test_render(self):
        try:
            import pygame
            settings = core.Settings(max_steps=20)
            core.Game(settings=settings, rendered=True).run()
        except ImportError:
            print("It looks like you don't have pygame installed, skipping the render test.")
        
    def test_field(self):
        f = core.FieldGenerator().generate()
        s = str(f)
        f2 = core.Field.from_string(s)
        self.assertEqual(f, f2)
        for i in xrange(1000):
            f = core.FieldGenerator(num_points=3, num_ammo=6).generate()
            self.assertEqual(len(f.find(core.Field.CONTROL)), 3)
            self.assertEqual(len(f.find(core.Field.AMMO)), 6)
        f3 = core.Field.from_string(SMALL_FIELD)
                
    def test_string_agent(self):
        game = core.Game(red=RANDOM_AGENT, 
                         blue=RANDOM_AGENT, 
                         rendered=False)
        game.run()
    
    def test_replay(self):
        settings = core.Settings(max_steps=200)
        for i in range(40):
            game = core.Game(settings=settings, record=True, rendered=False, verbose=False)
            game.run()
            replaygame = core.Game(replay=game.replay, rendered=False, verbose=False)
            replaygame.run()
            self.assertEqual(replaygame.score_red, game.score_red)
            
    def test_tournament(self):
        tmpdir = '_tmp'
        if not os.path.exists(tmpdir):
            os.mkdir(tmpdir)
        for l in 'abc':
            shutil.copy(core.DEFAULT_AGENT_FILE,os.path.join(tmpdir,'agent%s.py'%l))
            pickle.dump("This is agent %s's blob."%l, open(os.path.join(tmpdir,'agent%s_blob'%l),'wb'))
        tournament.full(folder='_tmp')
                    

# def check_balance():
#     scores = []
#     for i in range(10000):
#         game = core.Game('domination/agent_adjustable.py','domination/agent_adjustable.py',rendered=False, verbose=False).run()
#         scores.append(game.stats.score)
#         print "Average score %.5f std %.5f"%(mean(scores), stdev(scores))



def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDominationGame)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == "__main__":   
    run_tests()
