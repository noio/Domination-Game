import logging, os, re

# Declare the Django version we need.
from google.appengine.dist import use_library
use_library('django', '1.2')
import django

# Custom Django configuration.
# NOTE: All "main" scripts must import webapp.template before django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings
settings._target = None