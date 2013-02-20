### Imports ###

# Python imports
import os
import logging
import urllib
import random
import re
import platform
import math
from datetime import datetime, time, date, timedelta

# AppEngine imports
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext import blobstore
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import urlfetch


# Django imports
from django import forms
from django.shortcuts import render_to_response
from django.conf import settings as django_settings
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden
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
        if not request.user.is_admin:
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
    return respond(request, 'group.html', {'group':request.group, 
                                           'dgversion':core.__version__, 
                                           'pyversion':platform.python_version()})
    
def team(request, groupslug, team_id):
    team = models.Team.get_by_id(int(team_id), parent=request.group)
    return respond(request, 'team.html', {'team':team})
    
def brain(request, groupslug, brain_id):
    brain = models.Brain.get_by_id(int(brain_id), parent=request.group)
    return respond(request, 'brain.html', {'brain':brain})
    
def brain_download(request, groupslug, brain_id):
    brain = models.Brain.get_by_id(int(brain_id), parent=request.group)
    if ((request.user and request.user.is_admin) or
        brain.released()):
        response = HttpResponse(brain.source, content_type="application/python")
        response['Content-Disposition'] = 'attachment; filename=%s.py' % brain.identifier()
        return response
    return HttpResponseForbidden()
    
def game(request, groupslug, game_id):
    game = models.Game.get_by_id(int(game_id), parent=request.group)
    return respond(request, 'game.html', {'game':game})
    
def replay(request, groupslug, game_id):
    game = models.Game.get_by_id(int(game_id), parent=request.group)
    if game.replay:
        response = HttpResponse(content_type=game.replay.content_type)
        response['Content-Disposition'] = 'attachment; filename=replay%s.pickle.gz'%game.identifier()
        response['X-AppEngine-BlobKey'] = game.replay.key()
        return response
    return HttpResponseNotFound()
    
def download_data(request, groupslug, data_id):
    """ Download the binary data given in the data_id, 
        if the GET 'fn' is given, download under that filename,
        useful to set it to `agent_filename_blob`.
    """
    braindata = models.BrainData.get_by_id(int(data_id), parent=request.group)
    if braindata.blob:
        response = HttpResponse(content_type=braindata.blob.content_type)
        filename = request.GET.get('fn', braindata.filename)
        response['Content-Disposition'] = 'attachment; filename=%s'%filename
        response['X-AppEngine-BlobKey'] = braindata.blob.key()
        return response
    return HttpResponseNotFound()
    
    
def games_csv(request, groupslug):
    csv = memcache.get('games_csv')
    if csv is None:
        csv = 'time,red,blue,score_red,score_blue\n'
        for game in models.Game.all().ancestor(request.group).order('-added'):
            csv += '%s,%d,%d,%d,%d\n' % (game.added, game.red.key().id(), game.blue.key().id(), game.score_red, game.score_blue)
        memcache.add('games_csv', csv, 3600)
    return HttpResponse(csv,content_type='text/plain')
    
def brains_csv(request, groupslug):
    csv = memcache.get('brains_csv')
    if csv is None:
        csv = 'time,id,team,name\n'
        for brain in models.Brain.all().ancestor(request.group):
            csv += '%s,%d,%s,%s\n' % (brain.added, brain.key().id(), brain.identifier(), brain.name)
        memcache.add('brains_csv', csv, 3600)
    return HttpResponse(csv,content_type='text/plain')    


@team_required
def dashboard(request, groupslug):
    messages = []
    if request.method == 'POST':

        if 'newbrain' in request.POST:
            source = str(request.POST['newbrain']).strip() + '\n'
            source = re.sub(r'(\r\n|\r|\n)', '\n', source)
            if request.user.current_team.recent_upload_count() >= request.group.max_uploads:
                messages.append(("error", "Max uploads exceeded."))
            elif len(source) < 100:
                messages.append(("error","Code is too short."))
            else:
                if 'blobid' in request.POST and request.POST['blobid'].isdigit():
                    braindata = models.BrainData.get_by_id(int(request.POST['blobid']), parent=request.group)
                else:
                    braindata = None
                brain = models.Brain.create(team=request.user.current_team,
                            source=source, data=braindata)
                messages.append(("success","Brain uploaded."))

        if 'activebrains' in request.POST:
            brainids = []
            for letter in 'ABC':
                if 'brain-' + letter in request.POST:
                    brainids.append(int(request.POST['brain-'+letter]))
            request.user.current_team.activate(models.Brain.get_by_id(brainids, parent=request.group))

        if 'file' in request.FILES:
            d = models.BrainData.create(team=request.user.current_team, datafile=request.FILES['file'])

        return HttpResponseRedirect(reverse(dashboard, kwargs={'groupslug':groupslug}))
    upload_url = reverse(dashboard, kwargs={'groupslug':groupslug}) 
    # upload_url = blobstore.create_upload_url(reverse(upload_blob, kwargs={'groupslug':groupslug}))
    return respond(request, 'dashboard.html',{'messages':messages,'upload_url':upload_url})
    
@team_required
def upload_blob(request, groupslug):
    print "AAA"
    print request
    print dir(request)
    print "RAW" + request.raw_post_data
    print request.FILES
    upfile = request.FILES['file']
    print upfile
    print upfile.content_type
    print upfile.read()
    print upfile.__dict__
    print dir(upfile)

    return HttpResponseRedirect(reverse(dashboard, kwargs={'groupslug':groupslug}))
    # return HttpResponse('ok')

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
def settings(request, groupslug):
    """ Overview of group settings and teams """
    group = request.group
    if not group:
        return HttpResponseNotFound()
    if request.method == 'POST':
        if 'teamname' in request.POST:
            teamname = request.POST['teamname']
            team = models.Team.create(name=teamname, group=group)
            team.put()
        
        if 'teamid' in request.POST:
            team = models.Team.get_by_id(int(request.POST['teamid']), parent=request.group)
            if request.POST['bsubmit'] == 'Invite users':                
                team.send_invites([e.strip() for e in request.POST['emails'].split(',')])
            elif request.POST['bsubmit'] == 'Connect me':
                request.user.teams.append(team.key())
                request.user.teams = list(set(request.user.teams))
                request.user.put()
        
        if 'gamesettings' in request.POST:
            gamesettings = eval(request.POST['gamesettings'])
            if type(gamesettings) == dict:
                group.gamesettings = repr(gamesettings)
                group.put()
        
        if 'fieldascii' in request.POST:
            field = request.POST['fieldascii']
            if len(field) > 10:
                group.field = field.strip()
            else:
                group.field = None
            group.put()
        return HttpResponseRedirect(reverse(settings, kwargs={'groupslug':groupslug}))
    teams = models.Team.all().ancestor(group)
    return respond(request, 'settings.html', {'teams':teams})
    
### Task Views ###

# These don't have @admin_required, because they use a
# separate entry in app.yaml

def laddermatch(request):
    """ Runs a random match between two teams from each
        active group.
    """
    msg = ''
    for group in models.Group.all().filter("active", True):
        brains = group.brain_set.filter("active", True).fetch(10000)
        msg += '== Group %s ==\n'%(group)
        if brains:
            brains = sorted(brains,key=lambda b: (b.games_played, b.last_played))
            one = brains[0]
            brains = filter(lambda two: two != one, brains)
            if brains:
                two = random.choice(brains)
                if random.random() < 0.5:
                    one, two = two, one
                # Execute now if this is a direct request, queue if cron
                if 'X-AppEngine-Cron' in request.META:
                    deferred.defer(models.Game.play, group.key(), one.key(), two.key())
                else:
                    models.Game.play( group.key(), one.key(), two.key())
                msg += "Queued game %s vs %s.\n"%(one, two)
            else:
                msg += 'Not enough brains.\n'
    msg += "Success."
    logging.info(msg)
    return HttpResponse(msg)
    
def update_team_scores(request):
    """ Updates the scores of all teams from each group
    """
    msg = ''
    for group in models.Group.all().filter("active",True):
        for team in group.team_set:
            best = team.brain_set.filter("active",True).order("-conservative").get()
            if best is not None:
                msg += "%s's best score from %s is %.1f\n"%(team, best, best.conservative)
                team.maxscore = best.conservative
            else:
                team.maxscore = 0.0
            team.put()
    msg += 'Success'
    logging.info(msg)
    return HttpResponse(msg)
    
def clean(request):
    msg = ''
    for team in models.Team.all():
        if team.parent() is None:
            msg += 'Deleted %s\n' % (team)
            team.delete()
    for braindata in models.BrainData.all():
        if braindata.parent() is None:
            braindata.delete()
        if braindata.brain_set.count(1) == 0:
            braindata.delete()
    for brain in models.Brain.all():
        if brain.parent() is None:
            brain.delete()
    for game in models.Game.all():
        if game.parent() is None:
            game.delete()
    for account in models.Account.all():
        teams = filter(lambda t: t, models.Team.get(account.teams))
        account.teams = [t.key() for t in teams]
        account.put()
    # Clean blobs if they don't belong to replay or braindata
    for blob in blobstore.BlobInfo.all():
        if (datetime.now() - blob.creation > timedelta(days=1) and 
            models.Game.all().filter('replay =', blob.key()).count(1) == 0 and
            models.BrainData.all().filter('blob =', blob.key()).count(1) == 0):
            blob.delete()
    msg += 'Success\n'
    return HttpResponse(msg)
        
