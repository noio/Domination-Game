""" This module holds functions, exceptions and constants
    that are or might be used by both the game, renderer
    and perhaps the agents. By putting this code in a separate
    module, each of them can access it without requiring
    the other modules.
"""

### IMPORTS ###
import math
import time
import copy
from pprint import pprint
from heapq import heappush, heappop
from sys import maxint

# Local libs
from libs import astar


# Shortcuts
sqrt  = math.sqrt
try:
    inf = float('inf')
except ValueError:
    inf = 1e1000000
pi    = math.pi
astar = astar.astar

### EXCEPTIONS ###
class GameInterrupt(Exception):
    pass
    
### LISTS ###

def all_pairs(seq):
    l = len(seq)
    for i in range(l):
        for j in range(i+1, l):
            yield seq[i], seq[j]

### NUMERICAL ###

def frange(limit1, limit2 = None, increment = 1.):
    """ Like xrange, but for real numbers. 
    """
    if limit2 is None:
        limit2, limit1 = limit1, 0.
    else:
        limit1 = float(limit1)
    count = int(math.ceil((limit2 - limit1)/increment))
    return (limit1 + n*increment for n in xrange(count))
    
def mean(iterable):
    """ Returns mean of given list or generator."""
    s = 0.0
    n = 0
    for num in iterable:
        s += num
        n += 1
    return s/n
    
def stdev(iterable):
    """ Returns standard deviation of given list or generator.
        
        >>> stdev([1,2,3])
        1.0
    """
    nums = list(iterable)
    n = len(nums)
    avg = mean(nums)
    return sum((a - avg)**2 for a in nums)/float(max(n-1,1))

### GEOMETRY ###

def point_add(a, b):
    """ Add the coordinates of two points 
        (Inline this if you can, function calls are slow)
    """
    return (a[0] + b[0], a[1] + b[1])

def point_sub(a, b):
    """ Subtract two 2d vectors 
        (Inline this if you can, function calls are slow)
    """
    return (a[0] - b[0], a[1] - b[1])
    
def point_mul(a, f):
    """ Multiply a vector by a scalar 
        (Inline this if you can, function calls are slow)
    """
    return (a[0]*f, a[1]*f)
    
def point_dist(a, b):
    """ Distance between two points. """
    return ((a[0]-b[0]) ** 2 + (a[1]-b[1]) ** 2) ** 0.5


def line_intersects_rect(p0, p1, r):
    """ Check where a line between p1 and p2 intersects
        given axis-aligned rectangle r.
        Returns False if no intersection found.
        Uses the Liang-Barsky line clipping algorithm.
        
        >>> line_intersects_rect((1.0,0.0),(1.0,4.0),(0.0,1.0,4.0,1.0))
        ((0.25, (1.0, 1.0)), (0.5, (1.0, 2.0)))
        
        >>> line_intersects_rect((1.0,0.0),(3.0,0.0),(0.0,1.0,3.0,1.0))
        False
    """
    l,t,r,b = (r[0],r[1],r[0]+r[2],r[1]+r[3])
    p0x,p0y = p0
    q0x,q0y = p1
    t0,t1  = 0.0, 1.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    for edge in xrange(4):
        if edge == 0:
            p,q = -dx, -(l-p0x)
        elif edge == 1:
            p,q = dx, (r-p0x)
        elif edge == 2:
            p,q = -dy, -(t-p0y)
        else:
            p,q = dy, (b-p0y)
        if p == 0: # Parallel line
            if q < 0:
                return False
        else:
            ti = q/float(p)
            if p < 0:
                if ti > t1:
                    return False
                elif ti > t0:
                    t0 = ti
            else:
                if ti < t0:
                    return False
                elif ti < t1:
                    t1 = ti
    # Return (two) intersection coords
    return ((t0, (p0x + t0*dx, p0y + t0*dy)), (t1, (p0x + t1*dx, p0y + t1*dy)))
    
def line_intersects_circ((p0x,p0y), (p1x,p1y), (cx,cy), r):
    """ Computes intersections between line and circle. The line
        runs between (p0x,p0y) and (p1x,p1y) and the circle
        is centered at (cx,cy) with a radius r.
        Returns False if no intersection is found, and one or two intersection points otherwise. 
        Intersection points are (t, (x, y)) where t is the distance along the line between 0-1.
        (From stackoverflow.com/questions/1073336/circle-line-collision-detection)
        
        >>> line_intersects_circ((0,0), (4,0), (2,0), 1)
        [(0.25, (1.0, 0.0)), (0.75, (3.0, 0.0))]
        
        >>> line_intersects_circ((0,0), (2,0), (2,0), 1)
        [(0.5, (1.0, 0.0))]
        
        >>> line_intersects_circ((0,0), (0,1), (2,0), 1)
        False
    """
    dx, dy = p1x-p0x, p1y-p0y
    fx, fy = p0x-cx, p0y-cy
    
    a = dx*dx + dy*dy
    b = 2 * (dx*fx + dy*fy)
    c = (fx*fx + fy*fy) - r*r

    discriminant = b*b-4*a*c;
    if discriminant < 0:
        return False
    else:
        # ray didn't totally miss sphere, so there is a solution to the equation.
        discriminant = sqrt( discriminant );
        t1 = (-b - discriminant)/(2*a);
        t2 = (-b + discriminant)/(2*a);
        isects = []
        if t1 >= 0 and t1 <= 1:
            p1 = p0x + dx*t1, p0y + dy*t1
            isects.append((t1,p1))
        if t2 >= 0 and t2 <= 1:
            p2 = p0x + dx*t2, p0y + dy*t2
            isects.append((t2,p2))
        if not isects:
            return False
        else:
            return isects
        
        # // use t2 for second point

def line_intersects_grid((x0,y0), (x1,y1), grid, grid_cell_size=1):
    """ Performs a line/grid intersection, finding the "super cover"
        of a line and seeing if any of the grid cells are occupied.
        The line runs between (x0,y0) and (x1,y1), and (0,0) is the
        top-left corner of the top-left grid cell.
        
        >>> line_intersects_grid((0,0),(2,2),[[0,0,0],[0,1,0],[0,0,0]])
        True
        
        >>> line_intersects_grid((0,0),(0.99,2),[[0,0,0],[0,1,0],[0,0,0]])
        False
    """
    grid_cell_size = float(grid_cell_size)
    x0 = x0 / grid_cell_size
    x1 = x1 / grid_cell_size
    y0 = y0 / grid_cell_size
    y1 = y1 / grid_cell_size
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x = int(math.floor(x0))
    y = int(math.floor(y0))
    if dx != 0:
        dt_dx = 1.0 / dx
    else:
        dt_dx = inf
    if dy != 0:
        dt_dy = 1.0 / dy
    else:
        dt_dy = inf
    t = 0.0
    n = 1
    if (dx == 0):
        x_inc = 0
        t_next_horizontal = dt_dx
    elif (x1 > x0):
        x_inc = 1
        n += int(math.floor(x1)) - x
        t_next_horizontal = (math.floor(x0) + 1 - x0) * dt_dx
    else:
        x_inc = -1
        n += x - int(math.floor(x1))
        t_next_horizontal = (x0 - math.floor(x0)) * dt_dx
    if (dy == 0):
        y_inc = 0
        t_next_vertical = dt_dy
    elif (y1 > y0):
        y_inc = 1
        n += int(math.floor(y1)) - y
        t_next_vertical = (math.floor(y0) + 1 - y0) * dt_dy
    else:
        y_inc = -1
        n += y - int(math.floor(y1))
        t_next_vertical = (y0 - math.floor(y0)) * dt_dy
    while (n > 0):
        if grid[y][x] == 1:
            return True
        if (t_next_vertical < t_next_horizontal):
            y += y_inc
            t = t_next_vertical
            t_next_vertical += dt_dy
        else:
            x += x_inc
            t = t_next_horizontal
            t_next_horizontal += dt_dx
        n -= 1
    return False
    
def rect_contains_point(rect, point):
    """ Check if rectangle contains a point. """
    if (rect[0] <= point[0] and
        rect[1] <= point[1] and
        rect[0] + rect[2] >= point[0] and
        rect[1] + rect[3] >= point[1]):
        return True
    return False
    
def rect_offset(rect, offset):
    """ Offsets (grows) a rectangle in each direction. """
    return (rect[0] - offset, rect[1] - offset, rect[2]+2*offset, rect[3]+2*offset)
    
def rect_corners(rect):
    """ Returns cornerpoints of given rectangle.
    
        >>> rect_corners((1,2,1,3))
        ((1, 2), (2, 2), (2, 5), (1, 5))
    """
    tl = (rect[0],rect[1])
    tr = (rect[0]+rect[2],rect[1])
    br = (rect[0]+rect[2],rect[1]+rect[3])
    bl = (rect[0],rect[1]+rect[3])
    return (tl,tr,br,bl)
    
def rects_bound(rects):
    """ Returns a rectangle that bounds all given rectangles
    
        >>> rects_bound([(0,0,1,1), (3,3,1,1)])
        (0, 0, 4, 4)
    """
    def rb((ax,ay,aw,ah), (bx,by,bw,bh)):
        x = min(ax, bx)
        y = min(ay, by)
        w = max(ax+aw, bx+bw) - x
        h = max(ay+ah, by+bh) - y
        return (x,y,w,h)
    return reduce(rb, rects)

def rects_merge(rects):
    """ Merge a list of rectangle (xywh) tuples.
        Returns a list of rectangles that cover the same 
        surface. This is not necessarily optimal though.
        
        >>> rects_merge([(0,0,1,1),(1,0,1,1)])
        [(0, 0, 2, 1)]
    """
    def stack(rects, horizontal=False):
        """ Stacks rectangles that connect in either horizontal
            or vertical direction.
        """
        if horizontal:
            rects = [(y,x,h,w) for (x,y,w,h) in rects]
        rects.sort()
        newrects = []
        i = 0
        while i < len(rects):        
            (x1,y1,w1,h1) = rects[i]
            # Initialize new rect to this one
            nr = [x1,y1,w1,h1]
            # While the next rectangle connects to this one:
            while (i+1 < len(rects) and 
                    nr[0] == rects[i+1][0] and 
                    nr[2] == rects[i+1][2] and 
                    nr[1]+nr[3] == rects[i+1][1]):
                # Increase height of the current new rect
                nr[3] += rects[i+1][3]
                i += 1
            i += 1
            newrects.append(tuple(nr))
        # Flip rects back if we were stacking horizontally
        if horizontal:
            newrects = [(x,y,w,h) for (y,x,h,w) in newrects]
        return newrects
    # Stack twice, once in each direction
    return stack(stack(rects),horizontal=True)

def angle_fix(theta):
    """ Fixes an angle to a value between -pi and pi.
        
        >>> angle_fix(-2*pi)
        0.0
    """
    return ((theta + pi) % (2*pi)) - pi

### NAVIGATION ###

def reachable(grid, (x, y), border=1):
    """ Performs a 'flood fill' operation to find
        reachable areas on given tile map from (x,y). 
        Returns as binary grid with 1 for reachable.
        
        :param border:   can be a value or a function 
                         indicating borders of region

        >>> reachable([[0,1,0],[0,1,0]], (0,0))
        [[1, 0, 0], [1, 0, 0]]
    """
    w,h = len(grid[0]), len(grid)
    reachability = [[0 for _ in range(w)] for _ in range(h)]
    edge = [(x, y)]
    # If border is not a function, convert it to a simple compare
    if not hasattr(border, '__call__'):
        _border = border
        border = lambda x: (x == _border)
    while edge:
        newedge = []
        for (x, y) in edge:
            if 0 <= x < w and 0 <= y < h and not border(grid[y][x]) and reachability[y][x] != 1:
                reachability[y][x] = 1
                newedge.extend(((x+1, y), (x-1, y), (x, y+1), (x, y-1)))                
        edge = newedge
    return reachability
    
def grid_path_length((x,y),(gx,gy),g):
    #Path list (current coords, cost, expected cost)
    p = [((x,y),0,abs(gx-x)+abs(gy-y))]
    #Nodes visited
    h = []
    #Max values of coords
    m = (len(g[0]),len(g))
    while (len(p) > 0):
        #Sort based on best estimate of distance, with slight advantage 
        #to paths already explored
        p.sort(key=lambda o:0.99999*o[1]+o[2])
        #Best current loc
        (x,y) = p[0][0]
        l = []
        #Expand in all 4 directions, add if:
        #   1. Not of of bounds 2. No wall present 3. Not yet visited
        n = x-1
        if n >= 0 and g[y][n] == 0 and (n,y) not in h:
            l.append(((n,y),abs(gx-n)+abs(gy-y)))
        n = x+1
        if n < m[0] and g[y][n] == 0 and (n,y) not in h:
            l.append(((n,y),abs(gx-n)+abs(gy-y)))
        n = y-1
        if n >= 0 and g[n][x] == 0 and (x,n) not in h:
            l.append(((x,n),abs(gx-x)+abs(gy-n)))
        n = y+1
        if n < m[1] and g[n][x] == 0 and (x,n) not in h:
            l.append(((x,n),abs(gx-x)+abs(gy-n)))
        
        #Add all new valid paths to path list and history
        for i in l:
            if i[1] == 0:
                #Goal reached
                return p[0][1]+1
            h.append(i[0])
            p.append((i[0],p[0][1]+1,i[1]))
        #Remove old path
        del p[0]
    return None


def make_nav_mesh(walls, bounds=None, offset=7, simplify=0.001, add_points=[]):
    """ Generate an almost optimal navigation mesh
        between the given walls (rectangles), within
        the world bounds (a big rectangle).
        Mesh is a dictionary of dictionaries:
            mesh[point1][point2] = distance
    """
    # If bounds not given, assume outer walls are bounds.
    if bounds is None:
        bounds = rects_bound(walls)
    # 1) Offset walls and add nodes on corners
    walls = [rect_offset(w,offset) for w in walls]
    nodes = set(add_points)
    for w in walls:
        for point in rect_corners(w):
    # 2) Remove points that are inside of other walls (or outside bounds)
            other_walls = filter(lambda x: x!=w,walls)
            if (rect_contains_point(bounds, point) and 
                not any(rect_contains_point(ow, point) for ow in other_walls)):
                nodes.add((int(point[0]),int(point[1])))
    # 3) Connect nodes that can "see" eachother
    walls = [rect_offset(w,-0.001) for w in walls]
    mesh = dict((n,{}) for n in nodes)
    for n1 in nodes:
        for n2 in nodes:
            if n1 != n2:
                if not any(line_intersects_rect(n1,n2,w) for w in walls):
                    mesh[n1][n2] = point_dist(n1,n2)
    # 4) Remove direct connections that are not much shorter than indirect ones
    def astar_path_length(m, start, end):
        """ Length of a path from start to end """
        neighbours = lambda n: m[n].keys()
        cost       = lambda n1, n2: m[n1][n2]
        goal       = lambda n: n == end
        heuristic  = lambda n: point_dist(end, n)
        nodes, length = astar(start, neighbours, goal, 0, cost, heuristic)
        return length
    connections = []
    for n1 in mesh:
        for n2 in mesh[n1]:
            connections.append((mesh[n1][n2],(n1,n2)))
    connections.sort(reverse=True) # Start with the longest connections
    for length, (n1, n2) in connections:
        mesh[n1].pop(n2) # Remove connection to see best path without it
        alternative_dist = astar_path_length(mesh, n1,n2)
        # Put the connection back if the alternative is much worse
        if alternative_dist > (1+simplify) * length:
            mesh[n1][n2] = length
        
    return mesh


def find_path(start, end, mesh, grid, tilesize=16):
    """ Uses astar to find a path from start to end,
        using the given mesh and tile grid.
        
        >>> grid = [[0,0,0,0,0],[0,0,0,0,0],[0,0,1,0,0],[0,0,0,0,0],[0,0,0,0,0]]
        >>> mesh = make_nav_mesh([(2,2,1,1)],(0,0,4,4),1)
        >>> find_path((0,0),(4,4),mesh,grid,1)
        [(4, 1), (4, 4)]
    """
    # If there is a straight line, just return the end point
    if not line_intersects_grid(start, end, grid, tilesize):
        return [end]
    # Copy mesh so we can add temp nodes
    mesh = copy.deepcopy(mesh)
    # Add temp notes for start
    mesh[start] = dict([(n, point_dist(start,n)) for n in mesh if not line_intersects_grid(start,n,grid,tilesize)])
    # Add temp nodes for end:
    if end not in mesh:
        endconns = [(n, point_dist(end,n)) for n in mesh if not line_intersects_grid(end,n,grid,tilesize)]
        for n, dst in endconns:
            mesh[n][end] = dst
    
    neighbours = lambda n: mesh[n].keys()
    cost       = lambda n1, n2: mesh[n1][n2]
    goal       = lambda n: n == end
    heuristic  = lambda n: ((n[0]-end[0]) ** 2 + (n[1]-end[1]) ** 2) ** 0.5
    nodes, length = astar(start, neighbours, goal, 0, cost, heuristic)
    return nodes

### TIMING ###
tictocs = {}

def tic(timer_id='default'):
    try:
        tictocs[timer_id][0] = time.clock()
    except KeyError:
        tictocs[timer_id] = [time.clock(),0.0]

def toc(timer_id='default'):
    try:
        p, a = tictocs[timer_id]
        d = time.clock() - p
        tictocs[timer_id][1] *= 0.9
        tictocs[timer_id][1] += 0.1 * d
        return d
    except KeyError:
        tictocs[timer_id] = [time.clock(),0.0]
        return 0.0

def toc_avg(timer_id='default'):
    try:
        return tictocs[timer_id][1]
    except KeyError:
        return 0.0

if __name__ == "__main__":
    import doctest
    doctest.testmod()
