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

Another way to run a game is to create a Game object and call its `start()` method directly. This is mainly useful if you need some of the game's properties, like its `replay`.

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


Writing Agents
--------------