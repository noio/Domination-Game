from domination import core

# Setup
my_settings = core.Settings(max_steps=100)
my_game     = core.Game(red='domination/agent.py', blue='domination/agent.py', settings=my_settings)
# Run it
my_game.run()