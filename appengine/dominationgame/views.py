### Imports ###

# Python imports
import logging
import urllib
from datetime import datetime, time, date, timedelta

# AppEngine imports
from google.appengine.ext import db
from google.appengine.ext.db import Key
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
def admin_required(func):
    """Decorator that insists that you're logged in as administrator."""
    
    def admin_wrapper(request, *args, **kwds):
        if request.user is None:
            return HttpResponseRedirect(
                users.create_login_url(request.get_full_path().encode('utf-8')))
        if not request.user_is_admin:
            return HttpResponseForbidden('You must be admin for this function')
        return func(request, *args, **kwds)
    
    return admin_wrapper

### Page Handlers ###

def frontpage(request):
    """ Renders the frontpage/redirects to mobile front page
    """
    a = agent.AS_STRING
    g = core.Game(rendered=False, red_brain_string=a, blue_brain_string=a)
    g.run()
    return render_to_response('front.html', {'stats':g.stats})
