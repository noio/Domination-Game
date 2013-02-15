Using Scenarios
===============

Because most usage of the game will be more or less the same, some stuff has been automated in the form of a Scenario. Scenarios offer a way to define settings and score conditions, and automatically save the results of repeated runs.

For example, we subclass the Scenario module from domination.scenarios::

    import domination

    class MyScenario(domination.scenarios.Scenario) :
       REPEATS  = 10
       SETTINGS = core.Settings() 
       FIELD    = core.FieldGenerator().generate()
       
       def before_each():
           # Regenerate the field before each game.
           self.FIELD = core.FieldGenerator().generate()
    
We can now run our scenario and save the results::

    MyScenario.one_on_one('agent_one.py', 'agent_two.py', output_folder='results')


When a tournament is run, using :meth:`domination.scenarios.Scenario.tournament` a :class:`~domination.scenarios.MatchInfo` object is passed to the agent constructor.


Reference
---------

.. autoclass:: domination.scenarios.Scenario
   :members:
   
.. autoclass:: domination.scenarios.MatchInfo
   :members: