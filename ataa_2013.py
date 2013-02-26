#!/usr/bin/env python

import sys
import math
import os
import datetime
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

FIELD2 = """
w w w w w w w w w w w w w w w w w w w w w w w w w w w w w w w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ C _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ w w w w w w w w w w w w w w w _ _ _ _ _ _ _ w
w _ _ _ w _ _ _ w _ _ _ _ _ _ _ _ _ _ a _ _ _ _ _ _ w _ _ _ w
w R _ _ w _ _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ B w
w R _ _ w _ _ _ w _ _ _ _ w w w w w _ _ _ _ w _ _ _ w _ _ B w
w R _ _ w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w _ _ _ w _ _ B w
w _ _ _ w _ _ _ _ _ _ a _ _ _ _ _ _ _ _ _ _ w _ _ _ w _ _ _ w
w _ _ _ _ _ _ _ w w w w w w w w w w w w w w w _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ C _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ w
w w w w w w w w w w w w w w w w w w w w w w w w w w w w w w w
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

class Tournament2(scenarios.Scenario):
    REPEATS   = 2
    GENERATOR = None
    FIELD     = core.Field.from_string(FIELD2)
    SETTINGS  = core.Settings(max_steps=300,
                              max_score=100,
                              spawn_time=11,
                              ammo_amount=1,  
                              ammo_rate=9,
                              max_range=60,
                              max_see=80,
                              max_turn=math.pi/4,
                              think_time=0.06,
                              capture_mode=core.CAPTURE_MODE_MAJORITY)


# This is the code that is used for running a tournament, in order to run a 
# tournament in parallel, agents are temporarily copied, and blob data is not
# preserved. Please refer to "Running a Game" in the documentation for how
# to set up your own learning environment.
if __name__ == '__main__':
    # TODO: use argparse to set rendered true/false
    if len(sys.argv) == 1:
        Tournament2.test(red="domination/agent.py", blue="domination/agent.py")
    else:
        now = datetime.datetime.now()
        folder = os.path.join('tournaments', now.strftime("%Y%m%d-%H%M"))
        Tournament2.tournament(agents=sys.argv[1:], output_folder=folder, rendered=False)
# This is what is used to run the tournament:
