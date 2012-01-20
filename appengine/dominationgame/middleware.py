### Imports ###

# Python Imports
import logging

# AppEngine imports
from google.appengine.api import users

# Django imports
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse

# Local imports
import models, views

class AddUserToRequestMiddleware(object):
  """Add a user object and a user_is_admin flag to each request."""

  def process_view(self, request, view_func, view_args, view_kwargs):
    google_user = users.get_current_user()
    if google_user:
        request.user = models.Account.get_or_insert(google_user.nickname())
        request.user.google_user = google_user
        request.user.logout_url = users.create_logout_url('/')
    else:
        request.user = None
    request.user_is_admin = users.is_current_user_admin()