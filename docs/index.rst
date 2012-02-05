.. Domination Game documentation master file, created by
   sphinx-quickstart on Sat Feb  4 13:50:29 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Home
====

Contents:

.. toctree::
   :maxdepth: 2
   
   games
   agents
   scenarios
   fields


If you're not going to read any of the other documentation, just do the following. 

1. Modify or extend the basic agent found in the source code (`agent.py <https://github.com/noio/Domination-Game/blob/master/domination/agent.py>`_).

2. Import and extend the basic scenario::

    import domination.run
    
    class MyScenario(domination.run.Scenario):
       EPISODES = 10

3. Test to see if the scenario works as expected::

    ms = MyScenario('myagent.py', 'domination/agent.py')
    ms.test()

4. Run it, this will save the results to a comma-separated-value file::
    
	ms.run()

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
