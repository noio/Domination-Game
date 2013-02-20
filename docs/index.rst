.. Domination Game documentation master file, created by
   sphinx-quickstart on Sat Feb  4 13:50:29 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Home
====

Intro 
-----

The domination game is a game played by two teams of agents. They will combat one another and accumulate points through capturing control points on the map. The team with the most agents on a control point will capture that control point. These control points remain captured by the same team even when left alone. Agents are capable of picking up ammo, that spawns at designated positions on the map, and use it to shoot other agents. Upon death, agents will respawn in their teams' designated spawn areas. Agents can freely roam the map, but are unable to walk through walls or other agents.    

Within one iteration an agent can turn, change its speed, and shoot (in that order). To assure that simulations can terminate in reasonable time, there is a reaction time limit per iteration per agent. Simply, if the agent exceeds this limit it will not do anything. Map layouts (walls, control points and such) are known at the start of the game, but other info are not commonly known and have to be observed by the agents (ammopacks and agents). 

Contents
--------

.. toctree::
   :maxdepth: 2
   
   games
   agents
   scenarios
   fields
   utils
   libraries

Quickstart
----------

If you're not going to read any of the other documentation, just do the following. 

1. Copy and modify the basic agent found in the source code (`agent.py <https://github.com/noio/Domination-Game/blob/master/domination/agent.py>`_).

2. Make sure your folder structure looks like this (you only need the *domination* module):

  .. image:: ims/folderstructure.png

3. Create another file, put the following code in there, and run it::

	from domination import core
	
	# Setup
	my_settings = core.Settings(max_steps=100)
	my_game     = core.Game(red='my_agent.py', blue='domination/agent.py', settings=my_settings)
	# Run it
	my_game.run()  


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
