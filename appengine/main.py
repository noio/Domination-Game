import logging, os,sys

import appengine_config

# AppEngine imports.
from google.appengine.ext.webapp import util

# Import webapp.template.  This makes most Django setup issues go away.
from google.appengine.ext.webapp import template

# Import various parts of Django.
import django.core.handlers.wsgi
import django.core.signals
import django.db
import django.dispatch.dispatcher
import django.forms

def log_exception(*args, **kwds):
  """Django signal handler to log an exception."""
  cls, err = sys.exc_info()[:2]
  logging.exception('Exception in request: %s: %s', cls.__name__, err)

# Log all exceptions detected by Django.
django.core.signals.got_request_exception.connect(log_exception)

# Unregister Django's default rollback event handler.
django.core.signals.got_request_exception.disconnect(
    django.db._rollback_on_exception)

def main():
    application = django.core.handlers.wsgi.WSGIHandler()
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()