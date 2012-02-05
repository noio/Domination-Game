Running a Game
==============

In order to run a game, you need to import the domination module, and either create a :class:`~run.Scenario`, or create a :class:`~core.Game` object directly.


Creating a Game object directly
-------------------------------

The simplest way you can use the game object, is to just instantiate it and call its :py:meth:`~core.Game.run` method. This will run a game with all its default settings::

    core.Game('domination/agent.py','domination/agent.py').run()

However, creating a game object directly is useful mainly if you want to do some fiddling with its internals, so we recommend skipping right to :doc:`agents` or :doc:`scenarios`.

If we like, we can mess around a bit with the game object and its properties::

	import domination

	# Make it a short game
	settings = core.Settings(max_steps=20)

	# Initialize a game
	game = core.Game('domination/agent.py','domination/agent.py', 
	    record=True, rendered=False, settings=settings)

	# Will run the entire game.
	game.run() 

	# And now let's see the replay!
	replay = game.replay
	playback = core.Game(replay=replay)
	playback.run()

Game
----


The :class:`~core.Game` class has the following specification.

.. autoclass:: core.Game
   :members:
   
.. autoclass:: core.GameStats
   :members:

Settings
--------

.. autoclass:: core.Settings

The :py:attr:`Settings.capture_mode` can be one of:

.. autodata:: core.CAPTURE_MODE_NEUTRAL

.. autodata:: core.CAPTURE_MODE_FIRST

.. autodata:: core.CAPTURE_MODE_MAJORITY

The :py:attr:`Settings.end_condition` can be one of:

.. autodata:: core.ENDGAME_NONE

.. autodata:: core.ENDGAME_SCORE

.. autodata:: core.ENDGAME_CRUMBS

