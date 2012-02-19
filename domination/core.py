#!/usr/bin/env python
""" Domination game engine for Reinforcement Learning research.

This is the game engine module that can simulate games, without rendering them.
Refer to the readme for usage instructions.

"""
__author__ = "Thomas van den Berg and Tim Doolan"
MAJOR,MINOR,PATCH = 1,2,5
__version__ = '%d.%d.%d'%(MAJOR,MINOR,PATCH)

### IMPORTS ###
# Python
import random
import sys
import re
import os
import math
import time
import datetime
import itertools
import copy
import traceback
import bisect
import hashlib
import logging
from pprint import pprint
import cPickle as pickle

# Local
from utilities import *
from libs import *

# Shortcuts
sqrt = math.sqrt
try:
    inf = float('inf')
except ValueError:
    inf = 1e1000000
pi   = math.pi
sin  = math.sin
cos  = math.cos
rand = random.random

### CONSTANTS###
RANDOMSEED = 1597671198

TEAM_RED     = 0
TEAM_BLUE    = 1
TEAM_NEUTRAL = 2

CAPTURE_MODE_NEUTRAL  = 0 #: Controlpoints are neutral when occupied by both teams
CAPTURE_MODE_FIRST    = 1 #: Controlpoints stay in control of first team that captures them
CAPTURE_MODE_MAJORITY = 2 #: Controlpoints are owned by the team with the most occupiers

ENDGAME_NONE   = 0 #: End game when time expires
ENDGAME_SCORE  = 1 #: End game when either team has 0 score
ENDGAME_CRUMBS = 2 #: End game when all crumbs are picked up

DEFAULT_AGENT_FILE = os.path.join(os.path.dirname(__file__), 'agent.py')

AGENT_GLOBALS = globals().copy()

### CLASSES ###

class Settings(object):
    def __init__(self, max_steps=600,
                       max_score=1000,
                       max_turn=pi/3,
                       max_speed=40,
                       max_range=60,
                       max_see=100,
                       field_known=True,
                       ammo_rate=20,
                       ammo_amount=3,
                       agent_type='tank',
                       spawn_time=10,
                       tilesize=16,
                       think_time=0.010,
                       capture_mode=CAPTURE_MODE_NEUTRAL,
                       end_condition=ENDGAME_SCORE):
        """ Constructor for Settings class
        
            :param max_steps:     How long the game will last at most
            :param max_score:     If either team scores this much, the game is finished
            :param max_speed:     Number of game units each tank can drive in its turn
            :param max_turn:      The maximum angle that a tank can rotate in a turn
            :param max_range:     The shooting range of tanks in game units
            :param max_see:       How far tanks can see (Manhattan distance)
            :param field_known:   Whether the agents have knowledge of the field at game start
            :param ammo_rate:     How long it takes for ammo to reappear
            :param ammo_amount:   How many bullets there are in each ammo pack
            :param agent_type:    Type of the agents ('tank' or 'vacubot')
            :param spawn_time:    Time that it takes for tanks to respawn
            :param think_time:    How long the tanks have to do their computations (in seconds)
            :param capture_mode:  One of the CAPTURE_MODE constants.
            :param end_condition: One of the ENDGAME flags. Use bitwise OR for multiple.
            :param tilesize:      How big a single tile is (game units), change at risk of massive bugginess
        """            
        self.max_steps     = max_steps    
        self.max_score     = max_score    
        self.max_speed     = max_speed    
        self.max_turn      = max_turn     
        self.max_range     = max_range    
        self.max_see       = max_see      
        self.field_known   = field_known  
        self.ammo_rate     = ammo_rate    
        self.ammo_amount   = ammo_amount  
        self.agent_type    = agent_type   
        self.spawn_time    = spawn_time   
        self.think_time    = think_time   
        self.capture_mode  = capture_mode 
        self.end_condition = end_condition
        self.tilesize      = tilesize     
        # Validate
        if max_score % 2 != 0:
            raise Exception("Max score (%d) has to be even."%max_score)
        
    def __repr__(self):
        default = Settings()
        args = ('%s=%s'%(v,repr(getattr(self,v))) for v in vars(self) if getattr(self,v) != getattr(default,v))
        args = ', '.join(args)
        return 'Settings(%s)'%args
                
class GameStats(object):
    def __init__(self):
        self.score_red  = 0  #:The number of points scored by red
        self.score_blue = 0 #: The number of points scored by blue
        self.score      = 0.0 #: The final score as a float (red/total)
        self.steps      = 0 #: Number of steps the game lasted
        self.ammo_red   = 0 #: Number of ammo packs that red picked up
        self.ammo_blue  = 0 #: Idem for blue
        self.think_time_red  = 0.0 #: Total time in seconds that red took to compute actions
        self.think_time_blue = 0.0 #: Idem for blue
    
    def __str__(self):
        items = sorted(self.__dict__.items())
        maxlen = max(len(k) for k,v in items)
        return "== GAME STATS ==\n" + "\n".join(('%s : %r'%(k.ljust(maxlen), v)) for (k,v) in items)
        
class GameLog(object):
    """ Simple writable object that can replace
        sys.stdout
    """
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.log = []
        
    def write(self, string):
        if self.verbose and string != '\n':
            try:
                print >> sys.__stdout__, string
            except:
                pass
        self.log.append(string)
        
    def __str__(self):
        return ''.join(self.log)
        
class Game(object):
    
    """ The main game class. Contains game data and methods for
        simulation.
    """
    
    SIMULATION_SUBSTEPS = 10
    SIMULATION_MAXITER  = 20
    
    STATE_NEW       = 0
    STATE_READY     = 1
    STATE_RUNNING   = 2
    STATE_INTERRUPT = 3
    STATE_ENDED     = 4
        
    def __init__(self, red_brain=DEFAULT_AGENT_FILE,
                       blue_brain=DEFAULT_AGENT_FILE,
                       red_brain_string=None,
                       blue_brain_string=None,
                       settings=Settings(),
                       field=None,
                       red_init={},
                       blue_init={},
                       record=False,
                       replay=None,
                       rendered=True, 
                       verbose=True,
                       step_callback=None):
        """ Constructor for Game class 
            
            :param red_brain:         File that the red brain class resides in.
            :param blue_brain:        File that the blue brain class resides in.
            :param red_brain_string:  If passed, a string containing the blue brain class. 
                                        Overrides red_brain argument.
            :param blue_brain_string: Same as red_brain_string.
            :param settings:          Instance of the settings class.
            :param field:             An instance of Field to play this game on. 
            :param red_init:          A dictionary of keyword arguments passed to the red
                                        agent constructor.
            :param blue_init:         Like red_init.
            :param record:            Store all actions in a game replay.
            :param replay:            Pass a game replay to play it.
            :param rendered:          Enable/disable the renderer.
            :param verbose:           Print game log to output.
            :param step_callback:     Function that is called on every step. Useful for debugging.
        """
        self.record = record
        self.verbose = verbose
        
        # Public properties
        self.log = GameLog(self.verbose) #: The game log as an instance of class:`GameLog`
        self.red_raised_exception  = False #: Whether the red agents raised an exception
        self.blue_raised_exception = False #: Whether the blue agents raised an exception
        self.replay = replay #: The replay object, can be accessed after game has run
        self.stats = None #: Instance of :class:`~core.GameStats`.
        
        self.step_callback = step_callback
        if self.record and self.replay is not None:
            raise Exception("Cannot record and play replay at the same time.")
        # Set up a new game
        if replay is None:            
            self.settings = settings
            self.red_brain_string = red_brain_string if red_brain_string else open(red_brain,'r').read()
            self.blue_brain_string = blue_brain_string if blue_brain_string else open(blue_brain,'r').read()
            self.red_init = red_init
            self.blue_init = blue_init
            if field is None:
                self.field = FieldGenerator().generate()
            else:
                self.field = field
                self.settings.tilesize = self.field.tilesize
        # Load up a replay
        else:
            print 'Playing replay.'
            if replay.version != __version__:
                print >> sys.stderr, ("WARNING: Replay is for version %s, you have %s."%(replay.version, __version__))
            self.settings = replay.settings
            self.field = replay.field
            self.red_name = replay.red_name
            self.blue_name = replay.blue_name

        # Create the renderer if needed
        if rendered:
            self.add_renderer()
        else:
            self.renderer = None
        
        self.state = Game.STATE_NEW
        
    def _agent_name(self, agent_class):
        """ Retrieves the name of an agent
            This is defined by a static property NAME in the agent's class.
        """
        unsafe_chars = r'[^a-z0-9\-]+'
        if hasattr(agent_class, "NAME"):
            n = re.sub(unsafe_chars, '-', agent_class.NAME.lower())
            return n[:32]
        else:
            return "noname"
        
    def add_renderer(self, **kwargs):
        import renderer
        globals()['renderer'] = renderer
        self.renderer = renderer.Renderer(self.field, **kwargs)
        
    def _setup(self):
        """ Sets up the game.
        """
        # Redirect STDOUT
        self.old_stdout = sys.stdout
        sys.stdout = self.log
        # Print version
        print "Domination Game Ver. %s"%__version__
        # Read agent brains (from string or file)
        g = AGENT_GLOBALS.copy()
        if not self.replay:
            try:
                exec(self.red_brain_string, g)
                self.red_brain_class = g['Agent']
                self.red_name = self._agent_name(self.red_brain_class)
            except Exception, e:
                self.red_raised_exception = True
                print "Red agent has loading error"
                traceback.print_exc(file=sys.stdout)
                self.red_brain_class = None
                self.red_name = "error"
            # Blue brain
            try:
                exec(self.blue_brain_string, g)
                self.blue_brain_class = g['Agent']
                self.blue_name = self._agent_name(self.blue_brain_class)
            except Exception, e:
                self.blue_raised_exception = True
                print "Blue agent has loading error"
                traceback.print_exc(file=sys.stdout)
                self.blue_brain_class = None
                self.blue_name = "error"
            
        self.random = random.Random()
        self.random.seed(RANDOMSEED)
        # Initialize new replay
        if self.record:
            self.replay = ReplayData(self)
        # Load field objects
        allobjects = self.field.get_objects()
        cps = [o for o in allobjects if isinstance(o, ControlPoint)]
        reds = [o for o in allobjects if isinstance(o, TankSpawn) and o.team == TEAM_RED]
        blues = [o for o in allobjects if isinstance(o, TankSpawn) and o.team == TEAM_BLUE]
        # Game logic variables
        self.score_red   = self.settings.max_score / 2
        self.score_blue  = self.settings.max_score / 2
        self.step        = 0
        self.interrupted = False
        self.clicked     = None
        self.keys        = []
        # Simulation variables
        self.object_uid    = 0
        self.objects         = []
        self.broadphase_mov  = []
        self.broadphase_stat = []
        # Performance tracking
        self.stats = GameStats()
        self.think_time_red        = 0.0
        self.think_time_blue       = 0.0
        self.update_time_total     = 0.0
        self.sim_time              = 0.0
        self.sim_time_total        = 0.0
        # Game objects
        self.tanks         = []
        self.controlpoints = []
        for o in allobjects:
            self._add_object(o)
        self.controlpoints = cps
        # Initialize tanks
        print "Initializing agents."
        if self.record or self.replay is None:
            # Initialize new tanks with brains
            try:
                if self.red_brain_class is not None:
                    for i,s in enumerate(reds):
                        if self.settings.field_known:
                            brain = self.red_brain_class(i,TEAM_RED,settings=copy.copy(self.settings), 
                                        field_rects=copy.deepcopy(self.field.wallrects), field_grid=copy.deepcopy(self.field.wallgrid), 
                                        nav_mesh=copy.deepcopy(self.field.mesh), **self.red_init)
                        else:
                            brain = self.red_brain_class(i,TEAM_RED,settings=copy.copy(self.settings), **self.red_init)
                        t = Tank(s.x+2, s.y+2, s.angle, i, team=TEAM_RED, brain=brain, spawn=s, record=self.record)
                        self.tanks.append(t)
                        self._add_object(t)
            except Exception, e:
                self.red_raised_exception = True
                print "Red agent has __init__ error"
                traceback.print_exc(file=sys.stdout)
                
            try: 
                if self.blue_brain_class is not None:
                    for i,s in enumerate(blues):
                        if self.settings.field_known:
                            brain = self.blue_brain_class(i,TEAM_BLUE,settings=copy.copy(self.settings), 
                                        field_rects=copy.deepcopy(self.field.wallrects), field_grid=copy.deepcopy(self.field.wallgrid), 
                                        nav_mesh=copy.deepcopy(self.field.mesh), **self.blue_init)
                        else:
                            brain = self.blue_brain_class(i,TEAM_BLUE,settings=copy.copy(self.settings), **self.blue_init)
                        t = Tank(s.x+2, s.y+2, s.angle, i, team=TEAM_BLUE, brain=brain, spawn=s, record=self.record)
                        self.tanks.append(t)
                        self._add_object(t)
            except Exception, e:
                self.blue_raised_exception = True
                print "Blue agent has __init__ error"
                traceback.print_exc(file=sys.stdout)
            
        else:
            # Initialize tanks to play replays
            for i,(s,a) in enumerate(zip(reds,self.replay.actions_red)):
                t = Tank(s.x+2, s.y+2, s.angle, i, team=TEAM_RED, spawn=s, actions=a[:])
                self.tanks.append(t)
                self._add_object(t)
            for i,(s,a) in enumerate(zip(blues,self.replay.actions_blue)):
                t = Tank(s.x+2, s.y+2, s.angle, i, team=TEAM_BLUE, spawn=s, actions=a[:])
                self.tanks.append(t)
                self._add_object(t)
        self.tanks_red = [tank for tank in self.tanks if tank.team == TEAM_RED]
        self.tanks_blue = [tank for tank in self.tanks if tank.team == TEAM_BLUE]
        self.state = Game.STATE_READY
        self.interrupted = False
        
    def run(self):
        """ Start and loop the game. """
        if self.state != Game.STATE_READY:
            self._setup()
        res      = Game.SIMULATION_SUBSTEPS
        render   = self.renderer is not None
        settings = self.settings
        ## MAIN GAME LOOP
        self.state = Game.STATE_RUNNING
        try:
            for s in xrange(settings.max_steps):
                self.step = s+1
                if self.step % 10 == 0:
                    print "Step %d: %d - %d"%(self.step, self.score_red, self.score_blue)
                if self.step_callback is not None:
                    self.step_callback(self)
                ## UPDATE & CHECK VICTORY
                p = time.clock()
                for o in self.objects:
                    o.update()
                for t in self.tanks:
                    t.send_observation()
                for t in self.tanks:
                    t.get_action()
                # Compute shooting
                for tank in self.tanks:
                    if tank.shoots:
                        tcx, tcy = tank._x + tank.width/2, tank._y + tank.height/2
                        target = (cos(tank.angle) * settings.max_range + tcx, 
                                  sin(tank.angle) * settings.max_range + tcy)
                        hits   = self._raycast((tcx, tcy), target, exclude=tank)
                        tank._hitx, tank._hity = target
                        if hits:
                            t, (px,py), who = hits[0]
                            tank._hitx, tank._hity = px, py
                            if isinstance(who, Tank):
                                who.respawn_in = self.settings.spawn_time
                
                # Record times
                self.update_time_total += time.clock() - p
                sum_red = sum(tank.time_thought for tank in self.tanks_red)
                sum_blue = sum(tank.time_thought for tank in self.tanks_blue)
                self.stats.think_time_red += sum_red
                self.stats.think_time_blue += sum_blue
                if self.tanks_red:
                    self.think_time_red = sum_red / len(self.tanks_red)
                if self.tanks_blue:
                    self.think_time_blue = sum_blue / len(self.tanks_blue)
                # Score ending condition
                if ((self.settings.end_condition & ENDGAME_SCORE) and 
                    (self.score_red == 0 or self.score_blue == 0)):
                    break
                # No crumbs left ending condition
                if ((self.settings.end_condition & ENDGAME_CRUMBS) and
                    not any(True for o in allobjects if isinstance(o, Crumb))):
                    break
                ## RESET SOME STUFF
                if render:
                    self.clicked = None
                    self.keys = []
                ## SIMULATE AND RENDER
                for o in self.objects:
                    if o.movable:
                        o._dx = (o.x - o._x) / res
                        o._dy = (o.y - o._y) / res
                        if render:
                            o._da = (o.angle - o._a) / renderer.ROTATION_FRAMES
                # Render rotation/shooting
                if render:
                    for _ in xrange(renderer.ROTATION_FRAMES):
                        for o in self.objects:
                            o._a += o._da
                        self.renderer.render(self)
                    for f in xrange(renderer.SHOOTING_FRAMES):
                        self.renderer.render(self, shooting_frame = f)
                
                # Reset tanks that got shot
                for tank in self.tanks:
                    if tank.respawn_in == self.settings.spawn_time:
                        tank.ammo = 0
                        tank.x = tank._x = tank.spawn.x + 2
                        tank.y = tank._y = tank.spawn.y + 2
                        tank._dx = tank._dy = 0
                        tank.angle = tank._a = tank.spawn.angle                        
                
                # Simulate/Render movement
                self.sim_time = 0.0
                for step in xrange(res):
                    p = time.clock()
                    # Perform one physics substep
                    self._substep()
                    self.sim_time += time.clock() - p
                    if render:
                        self.renderer.render(self)
                self.sim_time_total += self.sim_time
                for o in self.objects:
                    if o.movable:
                        o.x = o._x
                        o.y = o._y
                        o._a = o.angle = angle_fix(o.angle)
        except GameInterrupt:
            self.state = Game.STATE_INTERRUPT
        except KeyboardInterrupt:
            self.state = Game.STATE_INTERRUPT
        self._end(interrupted=(self.state==Game.STATE_INTERRUPT))
        return self # For chaining, if you're into that.
    
    def _end(self, interrupted=False):
        """ End the game  and tells all the agents that the game
             is over so that they can write any remaining info.
        """
        if self.renderer is not None:
            self.renderer.quit()
        if interrupted:
            print "Game was interrupted."
            self.interrupted = True
        self.state = Game.STATE_ENDED
        self.stats.score_red = self.score_red
        self.stats.score_blue = self.score_blue
        self.stats.score = self.score_red / float(self.score_red + self.score_blue)
        self.stats.steps = self.step
        print self.stats
        if self.record:
            self.replay.settings = copy.copy(self.settings)
            self.replay.field = self.field
            self.replay.red_name = self.red_name
            self.replay.blue_name = self.blue_name
            self.replay.actions_red = [tank.actions for tank in self.tanks_red]
            self.replay.actions_blue = [tank.actions for tank in self.tanks_blue]
        # Finalize tanks brains.
        if self.record or self.replay is None:
            for tank in self.tanks:
                tank.brain.finalize(interrupted)
        # Set the stdout back to whatever it was before
        sys.stdout = self.old_stdout
    
    def _substep(self):
        """ Performs a single physics substep. All objects are moved by
            their respective _dx and _dy amounts, collisions are computed,
            and all objects are repeatedly separated until no large collisions
            occur anymore. 
        """
        for o in self.broadphase_mov:
            o._x += o._dx
            o._y += o._dy
            o._moved = True # if (o._dx != 0 or o._dy != 0) else False
        something_collided = True
        iteration = Game.SIMULATION_MAXITER
        pairs = set([])
        while something_collided and iteration > 0:
            self.broadphase_mov.sort(key=lambda o:(o._x))
            collisions = []
            k = 0
            for i, o1 in enumerate(self.broadphase_mov):
                for o2 in self.broadphase_mov[i+1:]:
                    # If the object didn't move, no need to check.
                    if o2._moved or o1._moved: 
                        # Break if the next object's _x is already outside
                        # this object's bounds. (The essential bit)
                        if o2._x >= o1._x + o1.width:
                            break
                        # Otherwise check if the y's intersect too
                        if o2._y < (o1._y + o1.height) and o1._y < (o2._y + o2.height):
                            sep = self._compute_separation(o1,o2)
                            if sep is not None:
                                if o1.solid and o2.solid:
                                    collisions.append(sep)
                                if (o1, o2) not in pairs:
                                    pairs.add((o2, o1))
                if o1._moved:
                    sf = True
                    for o2 in self.broadphase_stat[k:]:
                        # Maintain marker index for static broadphase
                        if o2._x + o2.width <= o1._x:
                            if sf:
                                k += 1
                            continue
                        elif sf:
                            sf = False
                        # Break if the next object's _x is already outside
                        # this object's bounds. (The essential bit)
                        if o2._x >= o1._x + o1.width:
                            break
                        # Otherwise check if the y's intersect too
                        if o2._y < (o1._y + o1.height) and o1._y < (o2._y + o2.height):
                            sep = self._compute_separation(o1,o2)
                            if sep is not None:
                                if o1.solid and o2.solid:
                                    collisions.append(sep)
                                if (o1, o2) not in pairs:
                                    pairs.add((o2, o1))
                    o1._moved = False
            something_collided = len(collisions) > 0
            # Sort the collisions on their first property, the penetration distance.
            collisions.sort(reverse=True, key=lambda c: c[0])
            for (p, o1, o2, px, py) in collisions:
                if p < 1: 
                    break
                if not o1._moved and not o2._moved:
                    if o1.movable:
                        if o2.movable:
                            dx = px/2
                            dy = py/2
                            o1._x += dx
                            o1._y += dy
                            o2._x -= dx
                            o2._y -= dy
                            o1._moved = True
                            o2._moved = True
                        else:
                            o1._x += px
                            o1._y += py
                            o1._moved = True
                    else:
                        o2._x -= px
                        o2._y -= py
                        o2._moved = True
            iteration -= 1
        pairs = sorted(pairs)
        for (o1,o2) in pairs:
            o1.collide(o2)
            o2.collide(o1)
        
    def _add_object(self,o):
        """ Add an object to the game and collision list. """
        o.game = self
        o.uid = hashlib.md5(str(self.object_uid)).digest()
        self.object_uid += 1
        self.objects.append(o)
        if o.physical:
            if o.movable:
                self.broadphase_mov.append(o)
                self.broadphase_mov.sort(key=lambda o:(o._x))
            else:
                self.broadphase_stat.append(o)
                self.broadphase_stat.sort(key=lambda o:(o._x))
        o.added_to_game(self)
        
    def _rem_object(self,o):
        """ Removes an object from the game and collision lists. """
        self.objects.remove(o)
        if o.physical:
            if o.movable:
                self.broadphase_mov.remove(o)
            else:
                self.broadphase_stat.remove(o)
        # Check if we need to remove this object from a parent
        if hasattr(o, 'parent'):
            o.parent.remove_child(o)
                
    def _get_objects_in_bounds(self, xmin, xmax, ymin, ymax, solid_only=True):
        """ Return a list of all objects whose bounding boxes
            intersect the given bounds.
        """
        for o in self.broadphase_mov:
            if o._x > xmax:
                break
            if (not solid_only or o.solid) and o._x + o.width > xmin:
                if ymin < (o._y + o.height) and o._y < ymax:
                    yield o
        for o in self.broadphase_stat:
            if o._x > xmax:
                break
            if (not solid_only or o.solid) and o._x + o.width > xmin:
                if ymin < (o._y + o.height) and o._y < ymax:
                    yield o
    
    def _compute_separation(self, object1, object2):
        """ Compute object separation/penetration
            Returns a tuple or None.
            The tuple consists of the penetration distance, 
            both objects, and the required movement of _object1_ 
            to separate.
        """
        # Find out what kind of collision we're dealing with
        # The circle proxy is either a real circle, or a rect's corner 
        # that another circle collides with.
        sep_as_circles   = False
        objects_switched = False
        if ((object1.shape == GameObject.SHAPE_CIRC) and
            (object2.shape == GameObject.SHAPE_CIRC)):
            circleproxy = (object1._x + object1.width, object1._y + object1.height, object1.width/2)
            sep_as_cicles = True
        elif ((object1.shape == GameObject.SHAPE_RECT) and
            (object2.shape == GameObject.SHAPE_RECT)):
            sep_as_circles = False
        else:
            if (object1.shape == GameObject.SHAPE_CIRC):
                objects_switched = True
                (object1, object2) = (object2, object1)
            cx   = object2._x + object2.width/2
            cy   = object2._y + object2.height/2
            ra   = object2.width/2
            l, t = object1._x, object1._y
            r, b = l + object1.width, t + object1.height
            if cx < l:
                if cy < t:
                    circleproxy    = (l,t,0.0)
                    sep_as_circles = True
                elif cy > b:
                    circleproxy    = (l,b,0.0)
                    sep_as_circles = True
            elif cx > r:
                if cy < t:
                    circleproxy = (r,t,0.0)
                    sep_as_circles = True
                elif cy > b: 
                    circleproxy = (r,b,0.0)
                    sep_as_circles = True
        # Separate Circle/Circle
        if sep_as_circles:
            (cx,cy,ra) = circleproxy
            md = ra + object2.width / 2 # Minimum distance
            dx = (cx + ra) - (object2._x + object2.width/2)
            dy = (cy + ra) - (object2._y + object2.height/2)
            ds = dx*dx + dy*dy          # Actual distance squared
            if ds < 0.01:
                p,px,py = 0.0, 0.0, 0.0
            elif ds < md*md:
                d  = sqrt(ds)   # Actual Distance
                p  = md - d     # Penetration amount
                f  = p/d
                px = f * dx
                py = f * dy
            else:
                return None
        # Separate Rect/Rect
        else:
            o1l, o1t = object1._x, object1._y
            o1r, o1b = o1l + object1.width, o1t + object1.height
            o2l, o2t = object2._x, object2._y
            o2r, o2b = o2l + object2.width, o2t + object2.height
            p,px,py  = inf, 0, 0
            # Try to find the side with the smallest separation distance
            pt = o1r - o2l # Left side penetration
            if 0 < pt:
                p, px, py  = pt, -pt, 0.0
            else:
                return None
            pt  = o1b - o2t # Top penetration
            if 0 < pt:
                if pt < p:
                    p, px, py = pt, 0.0, -pt
            else: 
                return None
            pt = o2r - o1l # Right side penetration
            if 0 < pt:
                if pt < p:
                    p, px, py = pt, pt, 0.0
            else:
                return None
            pt = o2b - o1t # Bottom penetration (really...)
            if 0 < pt:
                if pt < p:
                    p, px, py  = pt, 0.0, pt
            else:
                return None
        if objects_switched:
            object1, object2 = object2, object1
            px, py = -px, -py
        return (p, object1, object2, px, py)
        
    def _raycast(self, p0, p1, exclude=None):
        """ Shoots a ray from p0 to p1 and determines
            which objects are hit and at what time
            in the parametric line equation p0 + t*(p1-p0)
        """
        p0x, p0y = p0
        p1x, p1y = p1
        xmin, xmax = (p0x, p1x) if p0x < p1x else (p1x, p0x)
        ymin, ymax = (p0y, p1y) if p0y < p1y else (p1y, p0y)
        
        # List collided pairs
        in_box = self._get_objects_in_bounds(xmin,xmax,ymin,ymax)
        # Determine actual hits
        hits = []
        for o in in_box:
            if o != exclude:
                if o.shape == GameObject.SHAPE_RECT:
                    isect = line_intersects_rect(p0,p1,(o._x,o._y,o.width,o.height))
                    if isect:
                        # Append the t0 (intersection time) and object
                        hits.append((isect[0][0],isect[0][1],o))
                elif o.shape == GameObject.SHAPE_CIRC:
                    r = o.width/2
                    isect = line_intersects_circ(p0,p1,(o._x+r,o._y+r),r)
                    if isect:
                        # Append the t0 (intersection time), position and object
                        hits.append((isect[0][0],isect[0][1],o))
        hits.sort(key=lambda h: h[0])
        return hits
    
    def _click(self, pos):
        """ Tells the game that the right-mouse button was clicked
            somewhere on the field.
        """
        self.clicked = pos
    
    def _keypress(self, key):
        """ Tells the game that some key on the keyboard was pressed.
        """
        self.keys.append(key)
        
    def _select_tanks(self, rect, team=0):
        """ Function that is called by the renderer to set
            selected=True on tanks in the given rectangle. Handy
            for manually selecting and controlling tanks.
        """
        x,y,w,h = rect
        if w < 0:
            x += w
            w = -w
        if h < 0:
            y += h
            h = -h
        for t in self.tanks:
            if (t._x < x+w and 
                t._y < y+h and
                t._x + t.width > x and
                t._y + t.height > y) and t.team == team:
                t.selected = True
            else:
                t.selected = False 
    
    def __str__(self):
        args = ','.join(['%r'%self.red_name,
                         '%r'%self.blue_name,
                         'settings=%r'%self.settings])
        if self.red_init != {}:
            args += ',red_init=%r'%self.red_init
        if self.blue_init != {}:
            args += ',blue_init=%r'%self.blue_init
        return 'Game(%s)'%args


class Field(object):
    """ Class representing a playing field.
        
        You can use to_file, which dumps an ASCII representation of the
        field to a file, or you can pickle the entire Field object.
        Any way to create a Field is fine, the included FieldGenerator
        does a pretty good job!
    """
    # TILE MARKERS
    NOT       = '^'
    WALL      = 'W'
    AMMO      = 'A'
    SOURCE    = 'S'
    RED       = 'R'
    BLUE      = 'B'
    CONTROL   = 'C'
    CLEAR     = '_'
    REACHABLE = '.'
    
    def __init__(self, width, height, tilesize):
        # Settings variables
        self.width            = width
        self.height           = height
        self.tilesize         = tilesize
        
        # Initial empty tilemap with border
        # Create rows
        t         = [Field.WALL] * self.width
        m         = [Field.WALL] + [Field.CLEAR] * (self.width - 2) + [Field.WALL]
        b         = [Field.WALL] * self.width
        # Stack top + middle + bottom
        self.tiles = [t] + [m[:] for _ in xrange(self.height-2)] + [b]
        
        self._unpacked = None
    
    ## BUILTINS
    def __getstate__(self):
        """ Used for pickling, removes the _unpacked property """
        self._unpacked = None
        return self.__dict__
    
    def __str__(self):
        """ Returns the ASCII representation of this field """
        return '\n'.join([' '.join(row) for row in self.tiles])

    def __eq__(self, other):
        """ Equality, for testing purposes """
        return (self.width == other.width and
                self.height == other.height and
                self.tilesize == other.tilesize and
                self.tiles == other.tiles)
    
    ## SAVING/LOADING
    @classmethod
    def from_string(cls, s):
        """ Returns a new Field from given ASCII representation. """
        tiles = [[t.upper() for t in l.split()] for l in s.strip().split('\n')]
        h, w = len(tiles), len(tiles[0])
        field = cls(w, h, tilesize=16)
        field.tiles = tiles
        return field
    
    def to_file(self, filename):
        open(filename,'w').write(str(self))
    
    ## MANIPULATION
    def clone(self):
        """ Returns an exact copy of this field, that can
            be modified without changing this one. 
        """
        f = Field(self.width, self.height, self.tilesize)
        f.tiles = [r[:] for r in self.tiles]
        return f
        
    def find(self, match, bounds=None, mask=None):
        """ Find all (x,y) positions of given tile marker.
            e.g. field.find(Field.CONTROL) returns 
            positions of all controlpoints, (in tile coordinates).
        """
        if bounds is None:
            bounds = (0, 0, self.width, self.height)
        if match.startswith(Field.NOT):
            matches = lambda x: x not in match[1:]
        else:
            matches = lambda x: x in match
        found = []
        for i in xrange(bounds[1], bounds[3]):
            for j in xrange(bounds[0], bounds[2]):
                if matches(self.tiles[i][j]) and (mask is None or mask[i][j]):
                    found.append((j,i))
        return found
    
    def set(self, coords, marker, mirror=False, match='^'):
        """ Set tiles in coords to a marker, but only 
            if it matches the given match expression.
        """
        if match.startswith(Field.NOT):
            matches = lambda x: x not in match[1:]
        else:
            matches = lambda x: x in match
        # If only a single point was given, wrap it in list.
        if len(coords) and type(coords[0]) == int:
            coords = [coords]
        for i, (x,y) in enumerate(coords):
            if matches(self.tiles[y][x]):                
                self.tiles[y][x] = marker
                if mirror:
                    self.tiles[y][self.width-1-x] = marker
            
    def scatter(self, marker, num, pad=1, mirror=True):
        """ Scatter markers over the map, symmetrically or not."""
        midline = int(self.width / 2.0 + 0.5)
        if mirror:
            bounds = (pad, pad, midline-pad, self.height - pad)
            clear = self.find(Field.CLEAR, bounds=bounds)
            # Begin by scattering half of the points.
            points = random.sample(clear, num // 2)
            self.set(points, marker, mirror=True)
            # If odd number, add one more on midline:
            if num%2:
                bounds = (midline-1, pad, midline, self.height - pad)
                point = random.choice(self.find(Field.CLEAR, bounds=bounds))
                self.set(point, marker)
        else:
            # If not mirroring, just scatter the whole bunch.
            bounds = (pad, pad, self.width-1-pad, self.height-1-pad)
            clear = self.find(Field.CLEAR, bounds=bounds)
            points = random.sample(clear, num)
            self.set(points, marker)
                    
    def fill_unreachable(self):
        spawn = self.find(Field.RED)[0] or self.find(Field.BLUE)[0]
        reach = reachable(self.tiles, spawn, border=Field.WALL)
        reach = self.find(Field.CLEAR, mask=reach)
        # Mark reachable areas
        self.set(reach, Field.REACHABLE)
        # Set the rest to walls
        self.set(self.find(Field.CLEAR), Field.WALL)
        clear = self.find(Field.REACHABLE + Field.CLEAR)
        self.set(clear, Field.CLEAR)
                
    def valid(self):
        """ Check if map is valid, i.e. all points are
            reachable
        """
        spawn = self.find(Field.RED)[0] or self.find(Field.BLUE)[0]
        reachability = reachable(self.tiles, spawn, border=Field.WALL)
        for (x, y) in self.find(Field.AMMO + 
                                Field.CONTROL + 
                                Field.BLUE + 
                                Field.RED):
            if not reachability[y][x]:
                return False
        return True
        
    
    ## ACCESS BY GAME
    
    def unpack(self):
        """ Unpacks the tilemap and generates derivative
            properties like the navigation mesh, wall rects, 
            and game objects. Game objects are not
            actually created yet, but GENERATED ON THE FLY
            when the game asks for them, so that each
            game gets a shiny new batch of game objects.
        """
        _unpacked = {'wallrects':[],
                     'objects': [],
                     'mesh': None,
                     'grid': None}
        
        def create_object(x, y, marker):
            """ Creates an object from a tile marker """
            kwargs = {}
            if marker == Field.AMMO:
                cls = AmmoFountain
            elif marker == Field.SOURCE:
                cls = CrumbFountain
            elif marker == Field.CONTROL:
                cls = ControlPoint  
            elif marker == Field.RED:
                cls = TankSpawn
                kwargs.update({'angle': 0, 'team': TEAM_RED})
            elif marker == Field.BLUE:
                cls = TankSpawn
                kwargs.update({'angle': pi, 'team': TEAM_BLUE})
            else:
                raise Exception("Unknown map marker '%s'"%marker)
            offset = cls.SIZE/2.0 - self.tilesize/2.0
            kwargs['x'] = x * self.tilesize - offset
            kwargs['y'] = y * self.tilesize - offset
            return (cls, kwargs)
            
        # Unpacking tilemap
        for i, row in enumerate(self.tiles):
            for j, tile in enumerate(row):
                if tile == self.WALL:
                    _unpacked["wallrects"].append((j*self.tilesize, i*self.tilesize, self.tilesize, self.tilesize))
                elif tile not in self.CLEAR + self.REACHABLE:
                    _unpacked["objects"].append(create_object(j, i, tile))

        # Optimize the walls and generate Wall objects
        _unpacked['wallrects'] = rects_merge(_unpacked['wallrects'])
        _unpacked['objects'].extend( (Wall, {'x':x, 'y':y, 'width':w, 'height':h}) 
                                        for (x,y,w,h) in _unpacked['wallrects'] )
        
        # Generate nav mesh
        add_points = [(o.cx, o.cy) for o in _unpacked['objects'] if 
                        (isinstance(o,Ammo) or isinstance(o,ControlPoint))]
        _unpacked['mesh'] = make_nav_mesh(_unpacked['wallrects'], simplify=0.3,add_points=add_points)
        
        # Generate wall grid
        _unpacked['grid'] = [[(1 if t == self.WALL else 0) for t in row] for row in self.tiles]

        self._unpacked = _unpacked
        
    @property
    def mesh(self):
        if not self._unpacked: self.unpack()
        return self._unpacked['mesh']
    
    @property
    def wallgrid(self):
        if not self._unpacked: self.unpack()
        return self._unpacked['grid']
    
    @property
    def wallrects(self):
        if not self._unpacked: self.unpack()
        return self._unpacked['wallrects']
    
    def get_objects(self):
        """ Creates the gameobjects and returns them """
        if not self._unpacked: self.unpack()
        return [cls(**kwargs) for (cls, kwargs) in self._unpacked['objects']]
    
        
class FieldGenerator(object):
    """ Generates field objects from random distribution """

    def __init__(self, width=41, height=24, tilesize=16, mirror=True,
                       num_red=6, num_blue=6, num_points=3, num_ammo=6, num_crumbsource=0,
                       wall_fill=0.4, wall_len=(3,7), wall_width=4, 
                       wall_orientation=0.5, wall_gridsize=6):
        """ Create a FieldGenerator object with certain parameters for a random
            distribution of fields.
            
            :param width:            The width of the field in tiles
            :param height:           The height of the field in tiles
            :param tilesize:         The size of each tile (don't change from 16)
            :param mirror:           Make a symmetrical map
            :param num_blue:         The number of blue spawns
            :param num_red:          The number of red spawns
            :param num_points:       The number of controlpoints
            :param num_ammo:         The number of ammo locations on the map
            :param num_crumbsource:  The number of crumb fountains
            :param wall_fill:        What portion of the map is occupied by walls
            :param wall_len:         A range for the length of wall sections (min, max)
            :param wall_width:       The width of each wall section
            :param wall_orientation: The probability that each wall will be placed horizontally
                                     i.e. that the walls length will be along a horizontal axis
            :param wall_gridsize:    Place walls only at every n-th tile with their top-left 
        """
        self.width            = width
        self.height           = height
        self.tilesize         = tilesize
        self.mirror           = mirror
        self.num_red          = num_red
        self.num_blue         = num_blue
        self.num_points       = num_points
        self.num_ammo         = num_ammo
        self.num_crumbsource  = num_crumbsource
        self.wall_fill        = wall_fill
        self.wall_len         = wall_len
        self.wall_width       = wall_width
        self.wall_orientation = wall_orientation
        self.wall_gridsize    = wall_gridsize
    

    def generate(self):
        """ Generates a new field using the parameters for random 
            distribution set in the constructor. 
            
            :returns: A :class:`~domination.core.Field` instance.
        """
        # Create a new field
        field = Field(width=self.width, height=self.height, tilesize=self.tilesize)

        ## IMPORTANT OBJECTS
        # Add controlpoints
        field.scatter(Field.CONTROL, self.num_points, pad = 4, mirror=self.mirror)        
        # Add sources of crumbs
        field.scatter(Field.SOURCE, self.num_crumbsource, pad = 2, mirror=self.mirror)
        # Spawn regions
        spawn_h = int(sqrt(max(self.num_red, self.num_blue)) + 0.5) # height of the spawn block
        spawn_y = random.randint(1, self.height - 2 - spawn_h)      # y-pos of the spawn block
        for i in xrange(max(self.num_red, self.num_blue)):
            if i < self.num_red:
                x = 1 + i // spawn_h
                y = spawn_y + i%spawn_h
                field.set((x,y), Field.RED)
            if i < self.num_blue:
                x = self.width - 2 - i//spawn_h
                y = spawn_y + i%spawn_h
                field.set((x,y), Field.BLUE)

        ## WALLS
        midline = int(0.5 + self.width/2.0)
        # Add objects untill enough % is filled
        min_filled = self.height*self.width*self.wall_fill
        if len(self.wall_len) == 2:
            min_len, max_len = self.wall_len
        else:
            min_len, max_len = self.wall_len, self.wall_len
        attempts = 100
        while len(field.find('W')) < min_filled and attempts:
            new = field.clone()
            # Create horizontal section
            if rand() < self.wall_orientation:
                sec_width = random.randint(min_len,max_len)
                sec_height = self.wall_width
            # Create vertical section
            else:
                sec_width = self.wall_width
                sec_height = random.randint(min_len,max_len)
            # If map is mirrored, put stuff on left half only
            if self.mirror:
                x = random.randint(1, midline - sec_width)
                y = random.randint(1, self.height - sec_height - 1)
            else:
                x = random.randint(1, self.width - sec_width)
                y = random.randint(1, self.height - sec_height - 1)
            
            # Round to gridsize
            x = (x // self.wall_gridsize) * self.wall_gridsize
            y = (y // self.wall_gridsize) * self.wall_gridsize
            
            pts = new.find('W_.', bounds=(x, y, x + sec_width, y + sec_height))
            if len(pts) == sec_width*sec_height:
                new.set(pts, Field.WALL, self.mirror)
                if new.valid():
                    field = new
                    new.fill_unreachable()
                    continue                
            attempts -= 1
        
        # Clear walls under controlpoints
        for (x, y) in field.find(Field.CONTROL):
            for _y in xrange(y-1,y+2):
                for _x in xrange(x-1,x+2):
                    field.set((_x,_y), Field.CLEAR, match=Field.WALL)
        
        ## ITEMS
        field.scatter(Field.AMMO, self.num_ammo)
        
        return field


class GameObject(object):
    """ Generic game object """
    
    SHAPE_RECT = 0
    SHAPE_CIRC = 1
    
    SIZE       = 12
    
    def __init__(self, x=0.0, y=0.0, width=12, height=12, angle=0, shape=0, 
                       solid=True, movable=True, physical=True, graphic='default'):
        # Game variables
        self.uid      = -1
        self.x        = float(x)
        self.y        = float(y)
        self.width    = float(width)
        self.height   = float(height)
        self.angle    = float(angle)
        self.shape    = shape
        self.solid    = solid
        self.movable  = movable
        self.physical = physical
        self.graphic  = graphic   # Graphic used by the renderer.
        if not movable:
            self.cx = int(x + self.SIZE/2)
            self.cy = int(y + self.SIZE/2)
        # Internal vars, used by the collision detection
        self._x        = self.x
        self._y        = self.y
        self._a        = self.angle
        self._dx       = 0.0
        self._dy       = 0.0
        self._da       = 0.0
        self._moved    = False
        
    def added_to_game(self, game):
        """ Tells the object that it has been added to the game,
            that includes having its ".game" attribute set.
        """
        pass
        
    def update(self):
        """ Tells this object to update its game state.
            Only called once per game-step.
        """
        pass
        
    def collide(self, other):
        """ Informs the object that it has collided with another.
            Is called once per simulation substep.
        """
        pass
        
    def __eq__(self, other):
        return id(self) == id(other)
    
    def __ne__(self, other):
        return id(self) != id(other)
    
    def __lt__(self, other):
        return self.uid < other.uid
    
    def __cmp__(self, other):
        raise Exception("no sorting")
    
        
## Gameobject Subclasses

class Tank(GameObject):
    SIZE = 12
    SIZE_VACUBOT = 16
    
    def __init__(self,
                 x=0, y=0, angle=0, id=0, team=TEAM_RED,
                 brain=None, spawn=None, actions=None, record=False):
        super(Tank, self).__init__(x=x, y=y, angle=angle, width=self.SIZE, height=self.SIZE,
                    shape=GameObject.SHAPE_CIRC, solid=True, movable=True)
        if team == TEAM_RED:
            self.graphic = 'tank_red'
        else:
            self.graphic = 'tank_blue'
        self.brain       = brain
        self.id          = id
        self.team        = team
        self.ammo        = 0
        self.selected    = False
        self.shoots      = False
        self.respawn_in  = -1
        self.spawn       = spawn
        # A list of actions, either for recording or playing back.
        self.actions = actions if actions is not None else []
        self.record = record
        self.time_thought = 0.0
        # Additional hidden vars
        self._hitx = 0.0
        self._hity = 0.0
        self.grid_x = 0
        self.grid_y = 0
        
    def added_to_game(self, game):
        # Initialize observation
        self.observation = Observation()
        gridrng = (self.game.settings.max_see/2+1)//game.field.tilesize
        self.observation.walls = [[0 for _ in xrange(gridrng*2+1)] for _ in xrange(gridrng*2+1)]
        # Adjust settings for vacubot
        if game.settings.agent_type == 'vacubot':
            self.width = self.height = self.SIZE_VACUBOT
            if self.team == TEAM_RED:
                self.graphic = 'vacubot_red'
            else:
                self.graphic = 'vacubot_blue'
        
    def update(self):
        # Check alive status
        if self.respawn_in == 0:
            self.respawn_in = -1
        elif self.respawn_in > 0:
            self.respawn_in -= 1
            
    def send_observation(self):
        rng = self.game.settings.max_see
        obs = self.observation
        siz = self.width / 2.0
        obs.step       = self.game.step
        obs.loc        = mx, my = (int(self.x+siz), int(self.y+siz))
        obs.angle      = self.angle
        obs.ammo       = self.ammo
        obs.friends    = []
        obs.foes       = []
        obs.objects    = []
        obs.respawn_in = self.respawn_in
        obs.score      = (self.game.score_red, self.game.score_blue)
        obs.selected   = self.selected
        obs.clicked    = self.game.clicked
        obs.keys       = self.game.keys
        close = self.game._get_objects_in_bounds(self.x - rng, self.x + self.width + rng,
                    self.y - rng, self.y + self.height + rng, solid_only=False)
        
        for o in close:
            if isinstance(o, Tank):
                if o.team == self.team:
                    if o != self:
                        obs.friends.append((int(o._x+siz), int(o._y+siz)))
                else:
                    obs.foes.append((int(o._x+siz), int(o._y+siz), o._a))
            elif isinstance(o, Ammo):
                obs.objects.append((o.cx, o.cy, "Ammo"))
            elif isinstance(o, Crumb):
                obs.objects.append((o.cx, o.cy, "Crumb"))
        obs.cps = [(cp.cx,cp.cy,cp.team) for cp in self.game.controlpoints]
        # Observe walls
        f = self.game.field
        xj, yi = mx//f.tilesize, my//f.tilesize
        # Only regenerate grid if we moved to another cell.
        if xj != self.grid_x or yi != self.grid_y:
            gridrng = (rng/2+1)//f.tilesize
            w,h = f.width, f.height
            for oi,i in enumerate(xrange(yi-gridrng, yi+gridrng+1)):
                for oj,j in enumerate(xrange(xj-gridrng, xj+gridrng+1)):
                    if (i >= 0 and j >= 0 and i < h and j < w and
                        f.wallgrid[i][j] == 0):
                        obs.walls[oi][oj] = 0
                    else:
                        obs.walls[oi][oj] = 1
            self.grid_x = xj
            self.grid_y = yi
        if self.brain is not None:
            last_clock = time.clock()
            try:
                self.brain.observe(obs)
            except Exception, e:
                if self.team == TEAM_RED:
                    self.game.red_raised_exception = True
                else:
                    self.game.blue_raised_exception = True
                print "[Game]: Agent %s-%d raised exception:"%('RED' if self.team == 0 else 'BLU',self.id)
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60            
            self.time_thought = time.clock() - last_clock
        
    def get_action(self):
        ## Ask brain for action (or replay)
        if not self.record and self.actions:
            # print "i gots actions %s-%d"%('BLU' if self.team==TEAM_BLUE else 'RED',self.id)
            # print len(self.actions)
            (turn, speed, shoot) = self.actions.pop(0)
        else:
            last_clock = time.clock()
            try:
                (turn,speed,shoot) = self.brain.action()
            except Exception, e:
                if self.team == TEAM_RED:
                    self.game.red_raised_exception = True
                else:
                    self.game.blue_raised_exception = True
                print "[Game]: Agent %s-%d raised exception:"%('RED' if self.team == 0 else 'BLU',self.id)
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
                (turn,speed,shoot) = (0,0,False)
            self.time_thought += time.clock() - last_clock
            # Ignore action (NO-OP) if agent thought too long.
            if self.time_thought > self.game.settings.think_time:
                (turn, speed, shoot) = (0,0,False)
                print '[Game]: Agent %s-%d timed out (%.3fs).'%('RED'if self.team==0 else 'BLU',self.id,self.time_thought)
            if self.record:
                self.actions.append((turn,speed,shoot))
            if self.game.renderer is not None and self.game.renderer.active_team == self.team:
                self.brain.debug(self.game.renderer.agent_debug)
        self.shoots = False
        if self.respawn_in == -1:
            max_turn = self.game.settings.max_turn
            speed = min(self.game.settings.max_speed, speed)
            turn = max(-max_turn, min(max_turn, angle_fix(turn)))
            self.angle += turn
            self.x += math.cos(self.angle)*speed
            self.y += math.sin(self.angle)*speed
            # Process shooting
            if shoot and self.ammo > 0:
                self.shoots = True
                self.ammo -= 1
        self.observation.collided = False
        
    def collide(self, other):
        if isinstance(other, Tank):
            self.observation.collided = True
        elif isinstance(other, Wall):
            self.observation.collided = True
            

class Wall(GameObject):
    def __init__(self, **kwargs):
        kwargs['graphic'] = None
        kwargs['movable'] = False
        kwargs['solid'] = True
        super(Wall, self).__init__(**kwargs)

class ControlPoint(GameObject):
    SIZE = 24
    def __init__(self,x,y):
        super(ControlPoint, self).__init__(x=x, y=y, width=ControlPoint.SIZE, height=ControlPoint.SIZE, shape=GameObject.SHAPE_CIRC, 
                                           solid=False, movable=False, graphic='cp_neutral')
        self.team = TEAM_NEUTRAL
        self.collided = [0, 0, 0]
    
    def update(self):
        self.collided = [0, 0, 0]
        if self.team == TEAM_RED and self.game.score_red < self.game.settings.max_score:
            self.game.score_red += 1
            self.game.score_blue -= 1
        elif self.team == TEAM_BLUE and self.game.score_blue < self.game.settings.max_score:
            self.game.score_blue += 1
            self.game.score_red -= 1
    
    def collide(self, other):
        if isinstance(other, Tank):
            self.collided[other.team] += 1
            if self.game.settings.capture_mode == CAPTURE_MODE_NEUTRAL:
                if not (self.collided[TEAM_RED] and self.collided[TEAM_BLUE]):
                    self.team = other.team
                else:
                    self.team = TEAM_NEUTRAL
            if self.game.settings.capture_mode == CAPTURE_MODE_FIRST:
                if self.collided[self.team] == 0:
                    self.team = other.team
            elif self.game.settings.capture_mode == CAPTURE_MODE_MAJORITY:
                if self.team != other.team and self.collided[other.team] == self.collided[self.team]:
                    self.team = TEAM_NEUTRAL
                elif self.collided[other.team] > self.collided[self.team]:
                    self.team = other.team
            
            if self.team == TEAM_RED:
                self.graphic = 'cp_red'
            elif self.team == TEAM_BLUE:
                self.graphic = 'cp_blue'
            else:
                self.graphic = 'cp_neutral'
                

        
class Ammo(GameObject):
    """ Represents an ammo pack.
    """
    SIZE    = 16
    GRAPHIC = 'ammo_full'
    def __init__(self,x,y):
        super(Ammo, self).__init__(x=x, y=y, width=self.SIZE, height=self.SIZE, 
                                   shape=GameObject.SHAPE_CIRC, solid=False, 
                                   movable=False, graphic=self.GRAPHIC)
        self.pickedup = False
    
    def collide(self, other):
        if not self.pickedup and isinstance(other, Tank):
            if other.team == TEAM_RED:
                self.game.stats.ammo_red += 1
            elif other.team == TEAM_BLUE:
                self.game.stats.ammo_blue += 1
            other.ammo += self.game.settings.ammo_amount
            self.game._rem_object(self)
            self.pickedup = True

class Crumb(Ammo):
    """ Represents a crumb, something that can be picked
        up, with no other purpose than being registered
        as picked up. Essentially a small ammo packet.
    """
    SIZE = 4
    GRAPHIC = 'crumb'

class Fountain(GameObject):
    """ A non-physical object that spawns other objects at 
        regular intervals, or when there are too few
        of its 'child' objects on the map.
    """
    MIN_CHILDREN = 1
    DELAY        = 10
    CHILD_CLASS  = Ammo
    SIZE         = 16
    GRAPHIC      = None
    
    def SPREAD(self, x, y):
        return (x,y)
    
    def __init__(self, x, y):
        super(Fountain, self).__init__(x=x, y=y, width=self.SIZE, height=self.SIZE, 
                                   shape=GameObject.SHAPE_RECT, solid=False, 
                                   movable=False, physical=False, graphic=self.GRAPHIC)
        self.countdown = -1
        self.children = []
        self.initialized = False
        
    def added_to_game(self, game):
        for _ in xrange(self.MIN_CHILDREN):
            self.spawn_one()
        
    def update(self):
        # Charge slowly
        if self.countdown > -1:
            self.countdown -= 1         
        if self.countdown == -1 and len(self.children) < self.MIN_CHILDREN:
            self.countdown = self.DELAY
        if self.countdown == 0:
            self.spawn_one()
            
    def remove_child(self, child):
        self.children.remove(child)
            
    def spawn_one(self, attempts = 10):
        while attempts:
            (x,y) = self.SPREAD(self.x + self.width/2.0, self.y + self.height/2.0)
            f = self.game.field
            # Check if we're not spawning our object into a wall.
            (j,i) = int(x//f.tilesize), int(y//f.tilesize)
            if 0 <= i < f.height and 0 <= j < f.width and not f.wallgrid[i][j]:
                c = self.CHILD_CLASS(x - self.CHILD_CLASS.SIZE/2.0, y - self.CHILD_CLASS.SIZE/2.0)
                c.parent = self
                self.children.append(c)
                self.game._add_object(c)
                return
            attempts -= 1
            
class AmmoFountain(Fountain):
    MIN_CHILDREN = 1
    CHILD_CLASS  = Ammo
    GRAPHIC      = 'ammo_empty'
            
    def added_to_game(self, game):
        self.DELAY = self.game.settings.ammo_rate
        super(AmmoFountain, self).added_to_game(game)
                
class CrumbFountain(Fountain):
    MIN_CHILDREN = 200
    DELAY        = -1
    CHILD_CLASS  = Crumb
    
    def SPREAD(self, x, y):
        return x + self.game.random.gauss(0, 32), y + self.game.random.gauss(0, 32)

class TankSpawn(GameObject):
    SIZE = 16
    def __init__(self,x=0, y=0, angle=0, team=TEAM_RED, brain=None):
        super(TankSpawn, self).__init__(x=x, y=y, angle=angle, width=TankSpawn.SIZE, height=TankSpawn.SIZE, 
                                        shape=GameObject.SHAPE_RECT, solid=False, movable=False, physical=False)
        self.team = team
        self.graphic = 'spawn_red' if self.team == TEAM_RED else 'spawn_blue'

class Observation(object):
    def __init__(self):
        self.step       = 0     #: Current timestep
        self.loc        = (0,0) #: Agent's location (x,y)
        self.angle      = 0     #: Current angle in radians
        self.walls      = []    #: Visible walls around the agent: a 2D binary array
        self.friends    = []    #: All/Visible friends: a list of (x,y,angle)-tuples
        self.foes       = []    #: Visible foes: a list of (x,y,angle)-tuples
        self.cps        = []    #: Controlpoints: a list of (x,y,TEAM_RED/TEAM_BLUE)-tuples
        self.objects    = []    #: Visible objects: a list of (x,y,type)-tuples
        self.ammo       = 0     #: Ammo count
        self.score      = (0,0) #: Current game score
        self.collided   = False #: Whether the agent has collided in the previous turn
        self.respawn_in = -1    #: How many timesteps left before this agent can move again.
        # The following properties are only set when
        # the renderer is enabled:
        self.selected = False   #: Indicates if the agent is selected in the UI
        self.clicked = None     #: Indicates the position of a right-button click, if there was one
        self.keys = []          #: A list of all keys pressed in the previous turn
        
    def __str__(self):
        items = sorted(self.__dict__.items())
        maxlen = max(len(k) for k,v in items)
        return "== Observation ==\n" + "\n".join(('%s : %r'%(k.ljust(maxlen), v)) for (k,v) in items)
        

class ReplayData(object):
    """ Contains the replaydata for a game. """
    def __init__(self, game):
        self.settings = game.settings
        self.version = __version__
        self.actions_red  = [] # List of lists of red agents' actions
        self.actions_blue = [] # List of lists of blue agents' actions        

    def play(self):
        """ Convenience method for setting up a game to play this replay. 
        """
        g = Game(replay=self,rendered=True)
        g.run()
        return g

if __name__ == "__main__":
    g = Game(verbose=True, rendered=True).run()

