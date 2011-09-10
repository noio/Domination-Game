POI_CP = 0
POI_AMMO = 1
POI_SUPPORT = 2

class Agent(object):
    
    def __init__(self, id, team, settings=None, field_rects=None, field_grid=None, nav_mesh=None, handicap=0.0):
        """ Each agent is initialized at the beginning of each game.
            The first agent (id==0) can use this to set up global variables.
            Note that the properties pertaining to the game field might not be
            given for each game.
        """
        self.id = id
        self.team = team
        self.handicap = handicap
        self.mesh = nav_mesh
        self.grid = field_grid
        self.settings = settings
        self.goal = None
        
        if id == 0:
            self.poi    = self.__class__.poi = set([])
            self.agents = self.__class__.agents = []
        self.agents.append(self)
        self.costs = {}
        
        # Default turning direction
        self.face_to = 0 if (team == 0) else pi
    
    def observe(self, observation):
        """ Each agent is passed an observation using this function,
            before being asked for an action. You can store either
            the observation object or its properties to use them
            to determine your action. Note that the observation object
            is modified in place.
        """
        self.observation = observation
        self.loc = observation.loc
        # Add control points to points of interest
        if observation.step == 1:
            for x,y,team in observation.cps:
                self.poi.add((x,y,POI_CP))
                self.poi.add((x,y-self.settings.tilesize,POI_SUPPORT))
                self.poi.add((x,y+self.settings.tilesize,POI_SUPPORT))
        # Add ammo to points of interest
        for x,y,has_ammo in observation.aps:
            self.poi.add((x,y,POI_AMMO))
        
        # Check if agent reached goal.
        if self.goal is not None and point_dist(self.goal, observation.loc) < 12:
            self.goal = None
            
        ## COMPUTE COST OF EACH GOAL FOR EACH AGENT
        self.costs.update(((x,y),100) for (x,y,t) in self.poi)
        # First discount all goals that others have taken
        for ag in self.agents:
            if ag.goal is not None:
                if ag == self:
                    self.costs[ag.goal] -= 10 
                else:
                    self.costs[ag.goal] += 10
        # Compute costs for each point of interest
        for (x,y,t) in self.poi:
            # Dead agents have high costs
            if observation.respawn_in >= 0:
                self.costs[(x,y)] += 1000
            # Faraway agents have high costs
            self.costs[(x,y)] += (point_dist((x,y),observation.loc)**0.5)//2
            if t == POI_CP:
                if observation.ammo == 0:
                    self.costs[(x,y)] += 6
            elif t == POI_AMMO:
                self.costs[(x,y)] += 5
                if observation.ammo > 0:
                    self.costs[(x,y)] += 15
            elif t == POI_SUPPORT:
                self.costs[(x,y)] += 15
                if observation.ammo == 0:
                    self.costs[(x,y)] += 2
        
    def action(self):
        """ This function is called every step and should
            return a tuple in the form: (turn, speed, shoot)
        """
        obs = self.observation
        ts = self.settings.tilesize
        
        ## First agent solves role assignment problem
        if self.id == 0:
            pois = list(self.poi)
            cost_matrix = []
            for ag in self.agents:
                cost_matrix.append([ag.costs.get((x,y),100.0) for (x,y,t) in pois])
            m = munkres.Munkres()
            indexes = m.compute(cost_matrix)
            for agent,(aid, role) in zip(self.agents,indexes):
                agent.goal = pois[role][0:2]
        
        # Shoot enemies
        shoot = False
        target = None
        foes = filter(lambda f: not line_intersects_grid(self.loc, f[0:2], self.grid, ts), obs.foes)
        foes = sorted(foes,key=lambda f: point_dist(f[0:2],self.loc))
        if foes:
            if obs.ammo > 0 and point_dist(foes[0],self.loc) < self.settings.max_range:
                target = foes[0]
                shoot = True
            foe_rel = point_sub(foes[0][0:2],self.loc)
            # Face to last seen enemy
            self.face_to = math.atan2(foe_rel[1],foe_rel[0])
        
        # Compute path to goal
        if target is None:
            target = find_path(obs.loc, self.goal, self.mesh, self.grid, ts)[0]
            
        # Compute actual move
        dx = target[0]-obs.loc[0]
        dy = target[1]-obs.loc[1]
        if -1 < dx < 1 and -1 < dy < 1:
            dx = dy = 0
            turn = angle_fix(self.face_to-obs.angle)
            speed = 0
        else:
            turn = angle_fix(math.atan2(dy, dx)-obs.angle) + (rand()*0.2-0.1)
            speed = (dx**2 + dy**2)**0.5
        if turn > self.settings.max_turn or turn < -self.settings.max_turn:
            shoot = False
            if speed < self.settings.max_speed:
                speed = 0
        
        if rand() < self.handicap:
            turn = 0
            speed = rand()*self.settings.max_speed
        
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
        if self.observation.selected:
            pygame.draw.line(surface,(0,0,0),self.loc,self.goal)
        
    def finalize(self, interrupted=False):
        """ This function is called after the game ends, 
            either due to time/score limits, or due to an
            interrupt (CTRL+C) by the user. Use it to
            store any learned variables and write logs/reports.
        """
        pass
