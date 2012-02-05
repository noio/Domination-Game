Using Scenarios
===============

.. autoclass:: run.Scenario

Because most usage of the game will be more or less the same, some stuff has been automated in the form of a Scenario. Scenarios offer a way to define settings and score conditions, and automatically save the results of repeated runs.

For example, we subclass the Scenario module from domination.run::

	import domination

	class MyScenario(domination.run.Scenario) :
	   EPISODES = 10 # how many matches
	   SETTINGS = core.Settings() # the settings for the game, such as range, speed, etcetera
	   FIELD = core.FieldGenerator().generate() # the map for the games

    
We then create an instance of this new scenario::   

    ms = MyScenario('firstagent.py', 'secondagent.py')

    
We can now run our scenario and save the results::

    ms.run()
    ms.write_scores()
