### Imports ###

# Python Imports
import logging

# AppEngine imports
from google.appengine.api import users

class AddUserToRequestMiddleware(object):
  """Add a user object and a user_is_admin flag to each request."""

  def process_request(self, request):
    request.user = users.get_current_user()
    request.user_is_admin = users.is_current_user_admin()