### Imports ###

# Python imports
import os
import logging
import urllib
import random
from datetime import datetime, time, date, timedelta

# AppEngine imports
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import urlfetch


# Django imports
from django import forms
from django.shortcuts import render_to_response
from django.conf import settings as django_settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.template import Template, Context
from django.template.loader import render_to_string
from django.template import Context, Template, RequestContext
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils import simplejson

# Library imports
from domination import core, agent

# Local Imports
import models

### Constants ###

### Decorators for Request Handlers ###
def team_required(func):
    def team_wrapper(request, *args, **kwds):
        if not request.user.current_team:
            return HttpResponseRedirect(reverse(connect_account))
        return func(request, *args, **kwds)
    
    return team_wrapper
    
    
def login_required(func):
    """Decorator that redirects to the login page if you're not logged in."""
    
    def login_wrapper(request, *args, **kwds):
        if request.user is None:
            return HttpResponseRedirect(reverse(login))
        return func(request, *args, **kwds)
    
    return login_wrapper


def admin_required(func):
    """Decorator that insists that you're logged in as administrator."""
    
    def admin_wrapper(request, *args, **kwds):
        if request.user is None:
            return HttpResponseRedirect(reverse(login))
        if not request.user_is_admin:
            return HttpResponseForbidden('You must be admin for this function')
        return func(request, *args, **kwds)
    
    return admin_wrapper
    
### Helper functions ###

def respond(request, template, params={}):
    params['user'] = request.user
    if request.group:
        params['group'] = request.group
    return render_to_response(template, params)

### Page Handlers ###

def frontpage(request):
    """ Renders the frontpage """
    newest_group = models.Group.all().order("-added").get()
    if not newest_group:
        return HttpResponseRedirect(reverse(edit_groups))
    return HttpResponseRedirect(newest_group.url())

def login(request):
    if request.method == 'POST':
        openid = request.POST['openid']
        next = request.POST['next']
        return HttpResponseRedirect(users.create_login_url(next, federated_identity=openid))
    next = request.GET['next'] if 'next' in request.GET else '/'
    return respond(request, 'login.html',{'next':next})

@login_required
def connect_account(request):
    if request.method == 'POST':
        secret_code = request.POST['secret_code']
        team = models.Team.get_by_secret_code(secret_code)
        if team:
            if team not in request.user.teams:
                request.user.teams.append(team.key())
            request.user.put()
            return HttpResponseRedirect('/')
        return HttpResponse("Invalid code")
    secret_code = request.GET.get('c','')
    return respond(request, 'connect.html', {'secret_code':secret_code})

    
def group(request, groupslug):
    """ A group's home page, basically the front page """
    return respond(request, 'group.html', {'group':request.group})
    
def team(request, groupslug, team_id):
    team = models.Team.get_by_id(int(team_id), parent=request.group)
    return respond(request, 'team.html', {'team':team})
    
def brain(request, groupslug, brain_id):
    brain = models.Brain.get_by_id(int(brain_id), parent=request.group)
    return respond(request, 'brain.html', {'brain':brain})
    
def game(request, groupslug, game_id):
    game = models.Game.get_by_id(int(game_id), parent=request.group)
    return respond(request, 'game.html', {'game':game})

@team_required
def dashboard(request, groupslug):
    if request.method == 'POST':
        if 'newbrain' in request.POST:
            if len(request.POST['newbrain']) > 100:
                brain = models.Brain.create(team=request.user.current_team,
                            source=request.POST['newbrain'])
        if 'activebrains' in request.POST:
            brainids = []
            for letter in 'ABC':
                if 'brain-' + letter in request.POST:
                    brainids.append(int(request.POST['brain-'+letter]))
            request.user.current_team.activate(models.Brain.get_by_id(brainids, parent=request.group))
                    
    return respond(request, 'dashboard.html')

### Admin Handlers & Tasks ###

@admin_required
def edit_groups(request):
    """ Overview of groups """
    if request.method == 'POST':
        groupname = request.POST['groupname']
        group = models.Group(name=groupname)
        group.put()
        return HttpResponseRedirect(group.url())
    groups = models.Group.all()
    return respond(request, 'groups_edit.html', {'groups':groups})

@admin_required
def edit_teams(request, groupslug):
    """ Overview of teams and team names """
    group = models.Group.all().filter('slug =', groupslug).get()
    if not group:
        return Http404()
    if request.method == 'POST':
        if 'teamname' in request.POST:
            teamname = request.POST['teamname']
            team = models.Team.create(name=teamname, group=group)
            team.put()
        elif 'teamid' in request.POST:
            team = models.Team.get_by_id(int(request.POST['teamid']), parent=request.group)
            team.emails = [e.strip() for e in request.POST['emails'].split(',')]
            team.send_invites()
            team.put()
    teams = models.Team.all()
    return respond(request, 'teams_edit.html', {'teams':teams})
    

@admin_required
def laddermatch(request):
    op = ''
    for group in models.Group.all().filter("active", True):
        brains = group.brain_set.fetch(10000)
        if brains:
            one = random.choice(brains)
            # brains = filter(lambda two: two.team != one.team, brains)
            if brains:
                two = random.choice(brains)
                deferred.defer(models.Game.play, one.key(), two.key())
                # models.Game.play(one.key(), two.key())
                op += "%s queued game %s vs %s.\n"%(group, one, two)
    op += "Success."
    logging.info(op)
    return HttpResponse(op)
