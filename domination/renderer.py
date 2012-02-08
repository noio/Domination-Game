#!/usr/bin/env python
""" Renderer for domination game engine.

This is the rendering module for the Domination Game engine. To use it you 
need pygame, but you can run games without it. You'll never need to call
anything from this module explicitly. 

"""
__author__ = "Thomas van den Berg and Tim Doolan"

### IMPORTS ###
# Python 
import os
import time
import sys
import math

# Libraries
import pygame as pg

# Local
from utilities import *

# Shortcuts
pi         = math.pi
rad_to_deg = 180.0/pi 
cos        = math.cos
sin        = math.sin

### CONSTANTS

ASSETS_PATH = os.path.join(os.path.dirname(__file__),'assets')

C_RED               = (229,100,92)
C_BLUE              = (81,142,221)
SPF                 = 1/120.0 # Seconds per frame
ROTATION_FRAMES     = 6 # Number of frames for rotation animation
SHOOTING_FRAMES     = 10 # Number of frames for shooting animation
DRAW_BOUNDING_BOXES = False
DRAW_NAV_MESH       = True
DRAW_IDS            = False

### CLASSES ###
class Renderer(object):
    
    UI_HEIGHT           = 64
    UI_WIDTH            = 640
    
    """Renderer"""
    def __init__(self, field, skin=''):
        # Global pygame init
        pg.init()
        
        # Variables
        self.last_frame = 0.0
        self.render_time = 0.0
        self.paused = False
        self.active_team = 0
                
        # Setup screen/surfaces
        fw = field.width*field.tilesize # Field width and height
        fh = field.height*field.tilesize
        self.upscale = 1
        if fw < 400 and fh < 300:
            self.upscale = 2
        sw = max(fw*self.upscale, Renderer.UI_WIDTH)
        vp_x = (sw - fw*self.upscale) // 2
        ui_x = (sw - Renderer.UI_WIDTH) // 2
        self.vp_rect = [vp_x,0,fw*self.upscale, fh*self.upscale]
        # Set display mode
        self.screen  = pg.display.set_mode((max(self.vp_rect[2],Renderer.UI_WIDTH), self.vp_rect[3] + Renderer.UI_HEIGHT))
        self.ui_surf = self.screen.subsurface((ui_x,self.vp_rect[3],Renderer.UI_WIDTH, Renderer.UI_HEIGHT))
        self.vp_surf = pg.Surface((fw, fh))
        self.agent_debug = pg.Surface((fw,fh),flags=pg.SRCALPHA)
        self.agent_debug.fill((0,0,0,0))
        
        # Load assets
        self.font_mono = pg.font.Font(os.path.join(ASSETS_PATH,'proggy.ttf'), 16)
        self.font = pg.font.Font(os.path.join(ASSETS_PATH,'nokiafc22.ttf'), 16)
        self.font_small = pg.font.Font(os.path.join(ASSETS_PATH,'nokiafc22.ttf'), 8)
        self.ims = {
            "icon":self.load_texture("icon.png",skin),
            "default":self.load_texture("default.png",skin),
            "wall":self.load_texture("wall.png",skin),
            "autowall":self.load_texture("autowalls.png",skin),
            "floor":self.load_texture("floor.png",skin),
            "tank_red":self.load_texture("tank-red.png",skin),
            "tank_blue":self.load_texture("tank-blue.png",skin),
            "vacubot_red":self.load_texture("vacubot-red.png",skin),
            "vacubot_blue":self.load_texture("vacubot-blue.png",skin),
            "cp_red":self.load_texture("cp-red.png",skin),
            "cp_blue":self.load_texture("cp-blue.png",skin),
            "cp_neutral":self.load_texture("cp-neutral.png",skin),
            "spawn_red":self.load_texture("spawn-red.png",skin),
            "spawn_blue":self.load_texture("spawn-blue.png",skin),
            "muzzle":[self.load_texture("muzzle.png",skin).subsurface(i*32,0,32,32) for i in xrange(10)],
            "explode":[self.load_texture("explode.png",skin).subsurface(i*12,0,12,12) for i in xrange(10)],
            "ammo_empty":self.load_texture("ammo-empty.png",skin),
            "ammo_full":self.load_texture("ammo-full.png",skin),
            "crumb":self.load_texture("crumb.png",skin),
            "switch_red":self.load_texture("switch-red.png",skin),
            "switch_blue":self.load_texture("switch-blue.png",skin),
            "ui_overlay":self.load_texture("ui-overlay.png",skin),
            "ui_background":self.load_texture("ui-background.png",skin)
        }
        
        # Set up window
        pg.display.set_icon(self.ims['icon'])
        pg.display.set_caption("Domination Game")
        
        # Create a map surface
        self.mapsurface = pg.Surface((field.width*field.tilesize,field.height*field.tilesize))
        tile_fill(self.mapsurface, self.ims['floor'])
        draw_tilemap(self.mapsurface, field.wallgrid, self.ims['autowall'], field.tilesize)
        
        # Interface Elements
        self.render_stats   = pg.Surface((60,16))
        self.substep_stats  = pg.Surface((60,16))
        self.selection_rect = None
        self.mouse_down     = False
        
    def load_texture(self, name, skin=''):
        """ Looks up the tree for a sprite with the correct name,
            this allows skin packs to override only certain sprites.
        """
        path = os.path.join(ASSETS_PATH,skin)
        if path == ASSETS_PATH or os.path.exists(os.path.join(path,name)):
            return pg.image.load(os.path.join(path,name)).convert_alpha()
        else:
            return self.load_texture(name, os.path.split(skin)[0])
        
    def render(self, game, wait = True, shooting_frame=-1):
        self.handle_events(game)
        if wait:
            time.sleep(max(0, self.last_frame + SPF - time.clock()))
        scr             = self.screen
        vp              = self.vp_surf
        ui              = self.ui_surf
        self.last_frame = time.clock()
        scr.fill((71,71,71))
        ## MAP
        vp.blit(self.mapsurface,(0,0))
        ## DEBUG: MESH
        if DRAW_NAV_MESH:
            for n1 in game.field.mesh:
                for n2 in game.field.mesh[n1]:
                    pg.draw.line(vp,(120,180,120),n1,n2,2)
                pg.draw.circle(vp,(120,180,120),n1,3)
        ## OBJECTS
        for o in game.objects:                
            if o.graphic is None:
                continue
            bmp        = self.ims[o.graphic]
            dstx, dsty = int(o._x), int(o._y)
            w, h       = int(o.width), int(o.height)
            bmpw, bmph = bmp.get_rect().size
            # Render a rotated sprite
            if o._a != 0:
                (ocx,ocy) = bmp.get_rect().center
                degs      = -o._a*rad_to_deg
                # Use quick rotate for (almost) aligned sprites.
                if degs % 90 < 0.1:
                    bmp       = pg.transform.rotate(bmp,-o._a*rad_to_deg)
                else:
                    bmp       = pg.transform.rotozoom(bmp,-o._a*rad_to_deg,1)
                (ncx,ncy) = bmp.get_rect().center
                dstx -= ncx - ocx
                dsty -= ncy - ocy
                w,h = bmp.get_rect().size
                vp.blit(bmp, dest=(dstx,dsty), area=(0,0,w,h))            
            # Render rotated sprite using pre-rotated frames
            # if o._a != 0:
            #     frame = int((0.5 + 4*o._a/pi) % 8) 
            #     scr.blit(bmp, dest=(dstx,dsty), area=(w*frame,0,w,h))
            # Render fill sprite
            elif w > bmpw or h > bmph:
                tile_fill(vp, bmp, rect=(dstx,dsty,w,h))
            # Render normal sprite
            else:
                vp.blit(bmp, dest=(dstx,dsty,w,h), area=(0,0,w,h))
            # Render shooting
            if shooting_frame >= 0 and hasattr(o,'shoots'):
                if o.shoots:
                    cx,cy = int(o._x + o.width/2), int(o._y + o.height/2)
                    pg.draw.line(vp, (98,83,93), (cx, cy), (o._hitx, o._hity),1)
                    if shooting_frame < len(self.ims['muzzle']):
                        sbmp = self.ims['muzzle'][shooting_frame]
                        sbmp = pg.transform.rotate(sbmp, -o._a*rad_to_deg)
                        (ncx,ncy) = sbmp.get_rect().center
                        vp.blit(sbmp, dest=(cx - ncx,cy - ncy))
                if o.respawn_in == o.game.settings.spawn_time:
                    xbmp = self.ims['explode'][shooting_frame]
                    xbmp = pg.transform.rotate(xbmp, -o._a*rad_to_deg)
                    vp.blit(xbmp, dest=(dstx,dsty))
            if DRAW_BOUNDING_BOXES:
                if o.shape == 0: #rect
                    pg.draw.rect(vp, (255,255,0), (int(o._x),int(o._y),int(o.width), int(o.height)), 1)
                else:
                    pg.draw.ellipse(vp, (255,255,0), (int(o._x),int(o._y),int(o.width), int(o.height)), 1)
            if DRAW_IDS and hasattr(o, 'id'):
                txt = self.font_small.render("%d"%(o.id),False,(0,0,0))
                vp.blit(txt, dest=(dstx-txt.get_width(), dsty-txt.get_height()))
        
        # Selection/Overlay
        for t in game.tanks:
            if t.selected:
                pg.draw.rect(vp, (255,255,255), (t._x-2, t._y-2, t.width+4, t.height+4), 2)
        if self.selection_rect is not None and self.mouse_down:
            pg.draw.rect(vp, (255,255,255), self.selection_rect, 2)
        scr.blit(pg.transform.scale(vp, (self.vp_rect[2],self.vp_rect[3])), dest=(self.vp_rect[0],0))
        
        # Blit the agent's debug
        scr.blit(pg.transform.scale(self.agent_debug, (self.vp_rect[2],self.vp_rect[3])), dest=(self.vp_rect[0],self.vp_rect[1]))
        
        ## INTERFACE
        # Scores/Remaining time
        ui.blit(self.ims['ui_background'],dest=(0,0))
        ms = game.settings.max_score
        rs = game.score_red
        bs = game.score_blue
        txt = self.font.render("%d"%(game.score_red),False,C_RED)
        ui.blit(txt, dest=(62-txt.get_width(), 7))
        txt = self.font.render("%d"%(game.score_blue),False,C_BLUE)
        ui.blit(txt, dest=(260, 7))
        ui.fill(C_RED, (64,5, int(0.5+rs*192.0/ms),22))
        ui.fill(C_BLUE, (64+int(0.5+(ms-bs)*192.0/ms), 5, int(0.5+(bs)*192.0/ms), 22))
        txt = self.font.render("%d"%(game.settings.max_steps-game.step),False,(255,255,255))
        ui.blit(txt, dest=(356, 7))
        # Fill in the clock
        for a in range(int(game.step * (360.0/game.settings.max_steps))):
            a = (a - 90)/rad_to_deg
            pg.draw.line(ui,(255,255,255), (336,16), (int(336+cos(a)*9),int(16+sin(a)*9)),1)
        # Entire UI overlay
        ui.blit(self.ims['ui_overlay'],dest=(0,0))
        # Agent thinking time
        w = 24
        rw = w*(game.think_time_red/game.settings.think_time)
        bw = w*(game.think_time_blue/game.settings.think_time)
        ui.fill((238,221,207), (456,7,rw,8))
        ui.fill((238,221,207), (456,17,rw,8))
        if rw > w*0.75:
            rem = int(rw - w*0.75)
            ui.fill((255,0,0), (456+rw-rem,7,rem,8))
        if bw > w*0.75:
            rem = int(bw - w*0.75)
            ui.fill((255,0,0), (456+rw-rem,17,rem,8))
        txt = self.font_small.render("%dms"%(game.think_time_red*1000),False,(255,255,255))
        ui.blit(txt, dest=(482,7))
        txt = self.font_small.render("%dms"%(game.think_time_blue*1000),False,(255,255,255))
        ui.blit(txt, dest=(482,16))
        # LOWER LINE
        # Switch team button
        g = self.ims['switch_red'] if self.active_team == 0 else self.ims['switch_blue']
        ui.blit(g, (3,37))
        # Indicate mode
        m = "Simulating"
        if game.replay and not game.record:
            m = "Replay"
        elif game.record:
            m = "Recording"
        txt = self.font.render(m,False,(255,255,255))
        ui.blit(txt, dest=(120, 39))
        # Render time
        # txt = self.font_mono.render("R:% 3dms"%(self.render_time*1000),False,(255,255,255))
        # ui.blit(txt, dest=(500,3))
        # self.render_stats.scroll(dx=-1)
        # self.render_stats.fill((0,0,0),(59,0,1,30))
        # self.render_stats.fill((0,255,0),(59,15-int(self.render_time*1000),1,1))
        # ui.blit(self.render_stats, dest=(440,0))
        # # Substep time
        # txt = self.font_mono.render("S:% 3dms"%(game.sim_time*1000),False,(255,255,255))
        # ui.blit(txt, dest=(500,19))
        # self.substep_stats.scroll(dx=-1)
        # self.substep_stats.fill((0,0,0),(59,0,1,30))
        # self.substep_stats.fill((0,255,0),(59,15-int(game.sim_time*200),1,1))
        # ui.blit(self.substep_stats, dest=(440,16))
        
        # Flip buffers
        pg.display.flip()
        # Compute render time
        self.render_time = time.clock() - self.last_frame

    def handle_events(self, game):
        for event in pg.event.get():
            # Catch Quit events and CTRL+C
            if (event.type == pg.QUIT or 
                (event.type == pg.KEYDOWN and event.key == pg.K_c and (event.mod & pg.KMOD_CTRL))): 
                raise GameInterrupt()
            # Catch mouse button (left and right)
            elif event.type == pg.MOUSEBUTTONDOWN:
                (x,y) = event.pos
                if event.button == 1:
                    # Check if click was in viewport
                    if rect_contains_point(self.vp_rect,(x,y)):
                        self.selection_rect = [(x-self.vp_rect[0])//self.upscale,(y-self.vp_rect[1])//self.upscale,1,1]
                        self.mouse_down = True
                    # Check if a ui element was clicked
                    else:
                        uix,uiy = point_sub((x,y),self.ui_surf.get_offset())
                        # Clicked the team toggle
                        if rect_contains_point((6,37,58,22),(uix,uiy)):
                            self.toggle_team(game)
                elif event.button == 3:
                    game._click((x,y))
            # Catch mouse dragging for selection
            elif event.type == pg.MOUSEMOTION:
                x = (event.pos[0]-self.vp_rect[0])//self.upscale
                y = (event.pos[1]-self.vp_rect[1])//self.upscale
                if event.buttons[0] and self.mouse_down:
                    rx,ry,rw,rh = self.selection_rect
                    self.selection_rect = (rx,ry,x-rx, y-ry)
                    game.select_tanks(self.selection_rect,team=self.active_team)
            # Catch mouse release
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.mouse_down = False
                self.selection_rect = None
            # Catch space bar for pausing
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    self.paused = not self.paused
                    self.pause_loop(game)
                elif 97 <= event.key <= 122:
                    game._keypress(event.key)
                    
    def toggle_team(self,game):
        self.agent_debug.fill((0,0,0,0))
        self.active_team = 1-self.active_team
        game._select_tanks((0,0,0,0),team=self.active_team)
        
    def pause_loop(self,game):
        while self.paused:
            self.render(game)
            self.handle_events(game)
        
### HELPER FUNCTIONS ###
def tile_fill(surface, bitmap, rect=None, area=None):
    """ Fills the rect in the given surface with
        repeated tiles from area of bitmap
    """
    sx,sy,sw,sh = rect if rect is not None else surface.get_rect()
    bx,by,bw,bh = area if area is not None else bitmap.get_rect()
    for x in xrange(sx, sx+sw, bw):
        for y in xrange(sy, sy+sh, bh):
            a = (bx,by,min(bw, sx+sw-x),min(bh, sy+sh-y))
            surface.blit(bitmap, dest=(x,y), area=a)

def draw_tilemap(surface, tiles, graphic, tilesize):
    """ Draws a tilemap using the autotile algorithm. """
    T,R,B,L = 1,2,4,8;
    h,w     = len(tiles),len(tiles[0])
    idx     = 0
    s       = graphic.get_height()
    for i,row in enumerate(tiles):
        for j, tile in enumerate(row):
            if tile:
                idx = 0
                if i == 0 or tiles[i-1][j]:
                    idx += T
                if i == h-1 or tiles[i+1][j]:
                    idx += B
                if j == 0 or tiles[i][j-1]:
                    idx += L
                if j == w-1 or tiles[i][j+1]:
                    idx += R
                surface.blit(pg.transform.scale(graphic.subsurface(idx*s,0,s,s),(tilesize,tilesize)),(j*tilesize,i*tilesize))

if __name__ == "__main__":
    import core
    core.Game(core.DEFAULT_AGENT_FILE,core.DEFAULT_AGENT_FILE, rendered=True).run()
