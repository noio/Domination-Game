Running a Game
==============

In order to run a game, you need to import the domination module, and either create a :class:`~domination.run.Scenario`, or create a :class:`~domination.core.Game` object directly.


Creating a Game object directly
-------------------------------

The simplest way you can use the game object, is to just instantiate it and call its :py:meth:`~domination.core.Game.run` method. This will run a game with all its default settings::

    from domination import core
    core.Game(rendered=True).run() # Set rendered=False if you don't have pygame.

However, creating a game object directly is useful mainly if you want to do some fiddling with its internals, so we recommend skipping right to :doc:`agents` or :doc:`scenarios`.

If we like, we can mess around a bit with the game object and its properties::

	from domination import core

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

The :class:`~domination.core.Game` class has the following specification.

.. autoclass:: domination.core.Game
   :members:
   
.. autoclass:: domination.core.GameStats
   :members:
   
Replays
-------

Running replays is easy, first you need to unpack them::

    >>> import pickle
    >>> from domination import core
    >>> rp = pickle.load(open('replay20120215-1341_t2v1_vs_t6v1.pickle','rb'))
    >>> print rp
    <domination.core.ReplayData object at 0x10fca5fd0>

Then you call the play method::

    >>> rp.play()

.. autoclass:: domination.core.ReplayData
   :members:


Settings
--------

.. autoclass:: domination.core.Settings

The :py:attr:`Settings.capture_mode` can be one of:

.. autodata:: domination.core.CAPTURE_MODE_NEUTRAL

.. autodata:: domination.core.CAPTURE_MODE_FIRST

.. autodata:: domination.core.CAPTURE_MODE_MAJORITY

The :py:attr:`Settings.end_condition` can be one of:

.. autodata:: domination.core.ENDGAME_NONE

.. autodata:: domination.core.ENDGAME_SCORE

.. autodata:: domination.core.ENDGAME_CRUMBS

