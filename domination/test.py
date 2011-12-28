""" Testing module for Domination game engine

Running this script will test if the domination game is
working properly. This includes saving fields and replays.
"""

### IMPORTS

import unittest
import core
import run

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
    
    def setUp(self):
        self.settings = core.Settings()
        
    def test_basic(self):
        core.Game(rendered=False).run()
        
    def test_render(self):
        try:
            import pygame
            core.Game(rendered=True).run()
        except ImportError:
            print "Warning: It looks like you don't have pygame installed, skipping the render test."
                
    def test_string_agent(self):
        game = core.Game(red_brain_string=RANDOM_AGENT, 
                         blue_brain_string=RANDOM_AGENT, 
                         settings=self.settings,
                         rendered=False)
        game.run()
    
    def test_replay(self):
        settings = core.Settings(field_width=17, field_height=12, num_agents = 2, max_steps=200)
        for i in range(40):
            game = core.Game(settings=settings, record=True, rendered=False)
            game.run()
            replaygame = core.Game(replay=game.replay, rendered=False)
            replaygame.run()
            self.assertEqual(replaygame.score_red, game.score_red)

if __name__ == "__main__":
    unittest.main()