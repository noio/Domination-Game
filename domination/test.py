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
    
def test_replay():
    print "Testing replays..."
    settings = domination.Settings(field_width=17, field_height=12, num_agents = 2)
    game = domination.Game(settings=settings, 
                           red_brain_string=RANDOM_AGENT, 
                           blue_brain_string=RANDOM_AGENT, 
                           record=True,
                           rendered=False)
    game.run()
    score = game.score_red
    r = game.replay
    replaygame = r.play()
    if replaygame.score_red != score:
        raise Exception("Replay has different score from original game")
    print "Succes!"

if __name__ == "__main__":
    test_basic()
    test_string_agent()
    test_replay()
    