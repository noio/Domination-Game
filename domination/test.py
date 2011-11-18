""" Testing module for Domination game engine

Running this script will test if the domination game is
working properly. This includes saving fields and replays.
"""

import domination

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

def test_basic():
    print "Testing basic game..."
    settings = domination.Settings(max_steps=50)
    domination.run_games(settings=settings)
    game = domination.Game(settings=settings)
    game.run()
    print "Succes!"

def test_string_agent():
    print "Testing agents from strings..."
    settings = domination.Settings(max_steps=50)
    game = domination.Game(red_brain_string=RANDOM_AGENT, blue_brain_string=RANDOM_AGENT, settings=settings)
    game.run()
    print "Succes!"

if __name__ == "__main__":
    test_string_agent()
    test_basic()
    