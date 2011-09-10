Domination Game
===============

A simulation engine for a multi-agent competitive game. 


Running a Game
--------------

There are two ways to run a game, you can either start the engine using a command-line interface, or import it as a Python module, we recommend the latter.

### From Python

This is the recommended way of running a game. You can import the domination module, and call `run_games(path_to_red_agent, path_to_blue_agent)`, this function has arguments to expose pretty much all the functionality you need.

```python
from domination import domination
domination.run_games('domination/agent.py','domination/agent.py')
```

#### Creating the Game object directly

From Python you can also create a Game object and call its `start()` method directly. This is useful mainly if you need some of the game's properties, like its replay.

```python
from domination import domination

# Make it a short game
settings = domination.Settings(max_steps=20)

# Initialize a game
game = domination.Game('domination/agent.py','domination/agent.py', 
    record=True, rendered=False, settings=settings)

# Will run the entire game.
game.run() 

# And now let's see the replay!
replay = game.replay
playback = domination.Game(replay=replay)
playback.run()
```

### Using the command-line

If you're not using Python for your agent's evaluation scripts, you can also run the script from the command-line. Use the `-h` argument to see usage.

    ./domination.py -h
    
The most straightforward way to run a game would be as follows.

    ./domination.py -r agent.py -b agent.py


Writing Agents
--------------

Writing agents consists of creating a Python class that implements *five* methods, some of which are optional. The agents are imported using Python's [execfile method](http://docs.python.org/library/functions.html#execfile), after which the class named `Agent` is extracted. It is probably easiest to refer to and modify the [default agent](https://github.com/noio/Domination-Game/blob/master/domination/agent.py). But there is a quick rundown of the functions below as well.

The first thing you need to do is create a new file with a class named `Agent`.

```python
class Agent(object):
```
It needs to implement an `__init__` method that accepts a number of setup arguments. This method will be called for each agent at the beginning of each game.

```python
    def __init__(self, id, team, settings, field_rects, field_grid, nav_mesh, **kwargs):
```

The `settings` object is an instance of `Settings`, and contains all the game settings such as game length and maximum score. The `field_rects`,`field_grid`, and `nav_mesh` arguments provide some information about the map that the game will be played on. The first contains a list of walls on the map as `(x,y,width,height)` tuples, the second contains the same information, but as a 2D binary array instead. The third contains a graph that you can use for navigating the map, but more on that later.

Finally, you can provide extra arguments to "parametrize" your agents. You can set these arguments when you start a new game. For example, if your initialization looks as follows:

```python
    def __init__(self, id, team, settings, field_rects, field_grid, nav_mesh, aggressiveness):
```

Then you can set this parameter to different values when you start the game:

```python
domination.run_games('my_agent.py','opponent.py',red_init={'aggressiveness':10.0})
```

```python

class Agent(object):
    
    def __init__(self, id, team, settings=None, field_rects=None, field_grid=None, nav_mesh=None):
        """ Each agent is initialized at the beginning of each game.
            The first agent (id==0) can use this to set up global variables.
            Note that the properties pertaining to the game field might not be
            given for each game.
        """
        pass
        
    def observe(self, observation):
        """ Each agent is passed an observation using this function,
            before being asked for an action. You can store either
            the observation object or its properties to use them
            to determine your action. Note that the observation object
            is modified in place.
        """
        pass
        
    def action(self):
        """ This function is called every step and should
            return a tuple in the form: (turn, speed, shoot)
        """
        return (0,0,False)
        
    def debug(self, surface):
        """ Allows the agents to draw on the game UI,
            Refer to the pygame reference to see how you can
            draw on a pygame.surface. The given surface is
            not cleared automatically. Additionally, this
            function will only be called when the renderer is
            active, and it will only be called for the active team.
        """
        pass
        
    def finalize(self, interrupted=False):
        """ This function is called after the game ends, 
            either due to time/score limits, or due to an
            interrupt (CTRL+C) by the user. Use it to
            store any learned variables and write logs/reports.
        """
        pass
```

### The Observation

```python
class Observation(object):
    def __init__(self):
        self.step       = 0     # Current timestep
        self.loc        = (0,0) # Agent's location (x,y)
        self.angle      = 0     # Current angle in radians
        self.walls      = []    # Visible walls around the agent: a 2D binary array
        self.friends    = []    # All/Visible friends: a list of (x,y,angle)-tuples
        self.foes       = []    # Visible foes: a list of (x,y,angle)-tuples
        self.cps        = []    # Controlpoints: a list of (x,y,TEAM_RED/TEAM_BLUE)-tuples
        self.aps        = []    # Visible ammopacks: a list of (x,y)-tuples
        self.ammo       = 0     # Ammo count
        self.score      = (0,0) # Current game score
        self.collided   = False # Whether the agent has collided in the previous turn
        self.respawn_in = -1    # Respawn timer
        # The following properties are only set when
        # the renderer is enabled:
        self.selected = False   # Indicates if the agent is selected in the UI
        self.clicked = None     # Indicates the position of a right-button click, if there was one
        self.keys = []          # A list of all keys pressed in the previous turn
```
The imp