### Imports ###

# Python Imports
import os
import re
import hashlib
import logging
import base64 as b64
from datetime import datetime, date, time, timedelta

# AppEngine Imports
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext.db import Key
from google.appengine.api.app_identity import get_application_id, get_default_version_hostname

# Django Imports
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

# Local Imports
import views

### Constants ###
APP_URL = "http://localhost:8082"

### Exceptions ###

### Properties ###

class TimeDeltaProperty(db.Property):
    """ In seconds """
    def get_value_for_datastore(self, model_instance):
        td = super(TimeDeltaProperty, self).get_value_for_datastore(model_instance)
        if td is not None:
            return (td.seconds + td.days * 86400)
        return None
    
    def make_value_from_datastore(self, value):
        if value is not None:
            return timedelta(seconds=value)


class SlugProperty(db.StringProperty):
    """A (rough) App Engine equivalent to Django's SlugField."""
    
    def __init__(self, auto_calculate, **kwargs):
        """Initialize a slug with the property to base it on.
        """
        super(SlugProperty, self).__init__(**kwargs)
        self.auto_calculate = auto_calculate

    def get_value_for_datastore(self, model_instance):
        """Convert slug into format to go into the datastore."""
        value = self.auto_calculate.__get__(model_instance, None)
        return unicode(slugify(value))

    def validate(self, value):
        """Validate the slug meets formatting restrictions."""
        # Django does [^\w\s-] to '', strips, lowers, then [-\s] to '-'.
        if value and (value.lower() != value or ' ' in value):
            raise db.BadValueError("%r must be lowercase and have no spaces" % value)
        return super(SlugProperty, self).validate(value)

### Models ###

class Group(db.Model):
    name = db.StringProperty(required=True)
    slug = SlugProperty(name)
    added = db.DateTimeProperty(auto_now_add=True)
    
    def url(self):
        if self.slug is None:
            self.slug = slugify(self.name)
        return reverse(views.group, args=[self.slug])
    
class Team(db.Model):
    group = db.ReferenceProperty(Group)
    name = db.StringProperty(required=True)
    number = db.IntegerProperty(default=1)
    hashed_code = db.StringProperty(required=True)
    added = db.DateTimeProperty(auto_now_add=True)
    emails = db.StringListProperty()
    
    @classmethod
    def create(cls, **kwargs):
        kwargs['hashed_code'] = b64.urlsafe_b64encode(os.urandom(32))
        kwargs['number'] = Team.all().count() + 1
        return cls(**kwargs)
        
    @classmethod
    def get_by_secret_code(cls, secret_code):
        hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        return cls.all().filter('hashed_code =', hashed_code).get()

    def url(self):
        return reverse(views.team, args=[self.group.slug, self.key().id()])
        
    def send_invites(self):
        secret_code = b64.urlsafe_b64encode(os.urandom(32))
        self.hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        url = APP_URL + reverse(views.connect_account) + '?c=' + secret_code
        mailbody = """
                L.S.
                
                This is an invitation to join a team for the Domination game.
                You've been invited to join <strong>Team %d: %s</strong>.
                Use the following link to confirm:
                
                <a href='%s'>%s</a>
                
                Regards,
                
                Your TA
                """%(self.number, self.name, url,url)
        logging.info(mailbody)
        for email in self.emails:
            mail.send_mail(sender="noreply@%s.appspotmail.com"%get_application_id(),
                           to=email,
                           subject="Invitation to join a team for %s"%(self.group.name),
                           body=mailbody)
        self.put()

class Account(db.Model):
    team = db.ReferenceProperty(Team)
    added = db.DateTimeProperty(auto_now_add=True)
    
class Brain(db.Model):
    score = db.FloatProperty(default=100)
    uncertainty = db.FloatProperty(default=1)
    active = db.BooleanProperty(default=False)
    code = db.TextProperty(required=True)
    team = db.ReferenceProperty(Team)
    added = db.DateTimeProperty(auto_now_add=True)
