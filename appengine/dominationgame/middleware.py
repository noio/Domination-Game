### Imports ###

# Python Imports
import logging

# AppEngine imports
from google.appengine.api import users

# Django imports
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.core.urlresolvers import reverse

# Local imports
import models, views

class AddUserToRequestMiddleware(object):
  """Add a user object and a user_is_admin flag to each request."""

  def process_view(self, request, view_func, view_args, view_kwargs):
    google_user = users.get_current_user()
    if google_user:
        request.user = models.Account.get_or_insert(google_user.nickname(), nickname=google_user.nickname())
        request.user.google_user = google_user
        request.user.logout_url = users.create_logout_url('/')
        request.user.is_admin = users.is_current_user_admin()
    else:
        request.user = None
    models.Account.current_user = request.user

    

class ScopeToGroupMiddleware(object):
    """ Finds which group the user is looking at, and sets
        the user's current team to his team in that group.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        request.group = None
        if 'groupslug' in view_kwargs:
            request.group = models.Group.all().filter('slug =', view_kwargs['groupslug']).get()
            if not request.group:
                return HttpResponseNotFound()
            if request.user:
                team = models.Team.get(request.user.teams)
                if team is not None: 
                    team = filter(lambda t: t.group.key() == request.group.key(), team)
                    if team:
                        request.user.current_team = team[0]
                