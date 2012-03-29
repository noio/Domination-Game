
class Agent(object):
    
    NAME = "default_agent"
    
    def __init__(self, id, team, settings=None, field_rects=None, field_grid=None, nav_mesh=None, blob=None):
        """ Each agent is initialized at the beginning of each game.
            The first agent (id==0) can use this to set up global variables.
            Note that the properties pertaining to the game field might not be
            given for each game.
        """
        self.id       = id
        self.team     = team
        self.mesh     = nav_mesh
        self.grid     = field_grid
        self.settings = settings
        self.orders   = []
        self.goals    = []
        self.callsign = '%s-%d'% (('BLU' if team == TEAM_BLUE else 'RED'), id)
        
        # Read the binary blob, we're not using it though
        if blob is not None:
            print "Agent %s received binary blob of %s" % (
               self.callsign, type(pickle.loads(blob.read())))
            # Reset the file so other agents can read it.
            blob.seek(0) 
        
        # Recommended way to share variables between agents.
        if id == 0:
            self.all_agents = self.__class__.all_agents = []
        self.all_agents.append(self)
    
    def observe(self, observation):
        """ Each agent is passed an observation using this function,
            before being asked for an action. You can store either
            the observation object or its properties to use them
            to determine your action. Note that the observation object
            is modified in place.
        """
        self.observation = observation
        self.selected = observation.selected
                            
    def action(self):
        """ This function is called every step and should
            return a tuple in the form: (turn, speed, shoot)
        """
        turn, speed, shoot = 0, 0, False
        close_to_final = False
        obs = self.observation
        
        # Check if agent reached goal.
        if self.goals and point_dist(self.goals[0], obs.loc) < self.settings.tilesize / 2:
            if len(self.goals) > 1:
                self.goals.pop(0)
            else:
                close_to_final = True
        
        # Drive to where the agent died
        if obs.respawn_in == (self.settings.spawn_time - 1):
            self.goals = self.orders[:]
        
        # Drive to where the user clicked
        for (x, y, shift, selected) in obs.clicked:
            if selected:
                if shift:
                    self.orders.append((x,y))
                    self.goals.append((x,y))
                else:
                    self.orders =[(x,y)]
                    self.goals = [(x,y)]
        
        # Pick a "target"
        target = obs.foes[0] if obs.foes else None
        
        # Rotate towards target
        if target and not self.goals:
            dx = target[0]-obs.loc[0]
            dy = target[1]-obs.loc[1]
            turn = angle_fix(math.atan2(dy, dx) - obs.angle)
        
        # Shoot target
        if (obs.ammo > 0 and 
            target and 
            point_dist(target[0:2], obs.loc) <= self.settings.max_range + 6 and
            not line_intersects_grid(obs.loc, target[0:2], self.grid, self.settings.tilesize)):
            dx = target[0]-obs.loc[0]
            dy = target[1]-obs.loc[1]
            turn = angle_fix(math.atan2(dy, dx) - obs.angle)
            if turn > self.settings.max_turn or turn < -self.settings.max_turn:
                shoot = False
            else:
                shoot = True

        # Compute path, angle and drive
        if self.goals and not close_to_final:
            path = find_path(obs.loc, self.goals[0], self.mesh, self.grid, self.settings.tilesize)
            if path and not shoot:
                dx = path[0][0]-obs.loc[0]
                dy = path[0][1]-obs.loc[1]
                turn = angle_fix(math.atan2(dy, dx)-obs.angle)
                if abs(turn) > self.settings.max_turn:
                    speed = 0
                else:
                    speed = (dx**2 + dy**2)**0.5
        
        return (turn,speed,shoot)
        
    def debug(self, surface):
        """ Allows the agents to draw on the game UI,
            Refer to the pygame reference to see how you can
            draw on a pygame.surface. The given surface is
            not cleared automatically. Additionally, this
            function will only be called when the renderer is
            active, and it will only be called for the active team.
        """
        import pygame
        # First agent clears the screen
        if self.id == 0:
            surface.fill((0,0,0,0))
        # Selected agents draw their info
        if self.selected:
            prev = self.observation.loc
            for subgoal in self.goals:
                pygame.draw.line(surface,(0,0,0), prev, subgoal)
                prev = subgoal
        
    def finalize(self, interrupted=False):
        """ This function is called after the game ends, 
            either due to time/score limits, or due to an
            interrupt (CTRL+C) by the user. Use it to
            store any learned variables and write logs/reports.
        """
        pass
        
if __name__ == "__main__":
    import core
    core.Game('agent_controllable.py', 'agent.py').run()
    
