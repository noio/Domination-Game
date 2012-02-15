Creating Agents
===============

Writing agents consists of creating a Python class that implements *five* methods, some 
of which are optional. The agents are imported using Python's `exec method <http://docs.python.org/reference/simple_stmts.html#exec>`_, after which 
the class named `Agent` is extracted. It is probably easiest to refer to and modify 
the `default agent <https://github.com/noio/Domination-Game/blob/master/domination/agent.py>`_. 
But there is a quick rundown of the functions below as well.

The first thing you need to do is create a new file with a class named `Agent` 
that contains these 5 methods::

    class Agent(object):

        NAME = "my_agent" # Replay filenames and console output will contain this name.
    
        def __init__(self, id, team, settings=None, field_rects=None, field_grid=None, nav_mesh=None, **kwargs):
            pass
        
        def observe(self, observation):
            pass
        
        def action(self):
            return (0,0,False)
        
        def debug(self, surface):
            pass
        
        def finalize(self, interrupted=False):
            pass


Initialize
----------

It needs to implement an `__init__` method that accepts a number of setup arguments. 
This method will be called for each agent at the beginning of each game.

.. py:module: domination.agent

.. automethod:: domination.agent.Agent.__init__

The `settings` object is an instance of :class:`~domination.core.Settings`, and contains all the game 
settings such as game length and maximum score. The ``field_rects``, ``field_grid``, 
and ``nav_mesh`` arguments provide some information about the map that the game 
will be played on. The first contains a list of walls on the map as ``(x,y,width,height)``
tuples, the second contains the same information, but as a 2D binary array instead.

Navigation Mesh
^^^^^^^^^^^^^^^

Also passed to the agent constructor is a 'navigation mesh'. This is a directed graph containing **the set of points from which all points on the map can be seen**, and the straight lines connecting them. You can use it in conjunction with :meth:`~domination.utilities.find_path` to plan paths.

.. image:: ims/navmesh.png

It is structured as a dictionary where the keys are ``(x, y)`` tuples defining connectivity and distances. All connections are in this dictionary *two times*, both A → B and B → A are in there. The example below shows a point at ``(0, 0)`` connected to two other points, at ``(1, 0)`` and ``(0 ,2)``::

    {(0, 0): {(1, 0): 1.0, 
              (0, 2): 2.0},
     (1, 0): {(0, 0): 1.0},
     (0, 2): {(0, 0): 2.0}}
   
Agent Parameters
^^^^^^^^^^^^^^^^

Finally, you can provide extra arguments to "parametrize" your agents. You can set 
these arguments when you start a new game. For example, if your initialization looks as follows::

    def __init__(self, id, team, settings, field_rects, field_grid, nav_mesh, aggressiveness=0.0):

Then you can set this parameter to different values when you start the game::

    MyScenario('my_agent.py','opponent.py',red_init={'aggressiveness':10.0}).run()
    MyScenario('my_agent.py','opponent.py',red_init={'aggressiveness':20.0}).run()
    
Observe
-------

The second method you need to implement is ``observe``. This method 
is passed an *observation* of the current game state, depending on the settings, 
agents usually don't observe the entire game field, but only a part of it. Agents 
use this function to update what they know about the game, e.g. computing the most 
likely locations of enemies. The properties of the `Observation` object are listed below.

.. automethod:: domination.agent.Agent.observe

.. literalinclude:: ../domination/core.py
   :pyobject: Observation


Action
------

This is the most important function you have to implement. It should return a tuple containing 
a representation of the action you want the agent to perform. In this game, the action tuples
are supposed to look like ``(turn, speed, shoot)``. 

- **Turn** indicates how much your tank should spin around it's center.
- **Speed** indicates how much you want your tank to drive forward after it has turned.
- **Shoot** is set to True if you want to fire a projectile in this turn.

**Turn** is given in radians, and **Speed** is given in game units (corresponding to pixels
in the renderer). Note that any exceptions raised by your agent are ignored, and the agent
simply loses it's turn. Turn and speed are capped by the game settings.

.. automethod:: domination.agent.Agent.action


Debug
-----

Allows the agents to draw on the game UI, refer to the pygame reference to see how you can `draw <http://www.pygame.org/docs/ref/draw.html>`_ on a `pygame.surface <http://pygame.org/docs/ref/surface.html>`_. The given surface is not cleared automatically. Additionally, this function will only be called when the renderer is active, and it will only be called for the active team.

.. automethod:: domination.agent.Agent.debug


Finalize
--------

This method gives your agent an opportunity to store data or clean up after the game is finished. Learning agents could store their Q-tables, which they load up in ``__init__``.

.. automethod:: domination.agent.Agent.finalize


Communication
-------------

The recommended way to establish communication between agents is to define `static attributes <http://stackoverflow.com/questions/68645/static-class-variables-in-python>`_ in the ``Agent`` class definition. Static attributes are variables that are identical for every instance of the class, essentially, they are attributes of the *class*, not of the instances.

In Python, static variables can be defined in the class body, and accessed through the class definition. Be careful, setting ``Agent.attribute`` is quite different from setting ``my_agent = Agent(); my_agent.attribute``::

    class Agent:
        shared_knowledge = 1

        def __init__(self, etc):
            print Agent.shared_knowledge
            # is identical to
            print self.__class__.shared_knowledge
       
            # BUT THIS IS DIFFERENT:
            self.shared_knowledge = 5

(Binary) Data
-------------

You might want to supply your agent with additional (binary) data, for example a Q/value table, or some kind 
of policy representation. The convention for doing this is to pass an open file-pointer to the agent's constructor::

    Game(..., red_init={'blob': open('my_q_table','rb')} )

This is also the way that your data will be passed to the agent in the web app. If you have stored your data as a
pickled file, you can simply read it with::

    # In class Agent
    def __init__(..., blob=None ):
        if blob is not None:
            my_data = pickle.reads(blob.read())
            blob.seek(0) #: Reset the filepointer for the next agent.
                         #  if you omit this, the next agent will raise an EOFError
            
Of course, the way you store your data in this file is up to you, you can store it in any format, and even 
read it line-by-line if you want.