#!/usr/bin/env python

import sys
import math
from domination import core, scenarios

FIELD1 = """
w w w w w w w w w w w w w w w w w w w w w w w w w w w w w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ w _ C _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ w _ _ _ w w w w w w w w w w w _ _ _ _ _ _ w
w _ _ w _ _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ w
w R _ w _ _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ B w
w R _ w _ _ _ w _ A _ _ w w w w w _ _ A _ w _ _ _ w _ B w
w R _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ _ w _ B w
w _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ _ w _ _ w
w _ _ _ _ _ _ w w w w w w w w w w w _ _ _ w _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ C _ w _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w w w w w w w w w w w w w w w w w w w w w w w w w w w w w
"""

class Tournament1(scenarios.Scenario):
    REPEATS   = 1000
    GENERATOR = None
    FIELD     = core.Field.from_string(FIELD1)
    SETTINGS  = core.Settings(max_steps=300,
                              max_score=100,
                              spawn_time=10,
                              ammo_amount=1,  
                              ammo_rate=9,
                              max_range=60,
                              max_see=80,
                              max_turn=math.pi/4,
                              think_time=0.06,)



if __name__ == '__main__':
    if len(sys.argv) == 0:
        Tournament1.test(red="domination/agent.py", blue="domination/agent.py")
    else:
        Tournament1.tournament(agents=sys.argv[1:], output_folder='_tmp')        
# This is what is used to run the tournament:
