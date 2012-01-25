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

# Library Imports
from domination import core as domcore

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
    active = db.BooleanProperty(default=True)
    
    def __str__(self):
        return self.name
    
    def url(self):
        if self.slug is None:
            self.slug = slugify(self.name)
        return reverse(views.group, args=[self.slug])
        
    def ladder(self):
        recent = datetime.now() - timedelta(days=7)
        q = self.brain_set.filter('last_active > ',recent)
        return sorted(q, key=lambda b: b.conservative, reverse=True)
    
class Team(db.Model):
    group       = db.ReferenceProperty(Group, required=True)
    name        = db.StringProperty(required=True)
    number      = db.IntegerProperty(default=1)
    brain_ver   = db.IntegerProperty(default=0)
    hashed_code = db.StringProperty(required=True)
    added       = db.DateTimeProperty(auto_now_add=True)
    emails      = db.StringListProperty()
    
    @classmethod
    def create(cls, group, **kwargs):
        kwargs['hashed_code'] = b64.urlsafe_b64encode(os.urandom(32))
        kwargs['number'] = Team.all().count() + 1
        return cls(group=group, **kwargs)
        
    @classmethod
    def get_by_secret_code(cls, secret_code):
        hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        return cls.all().filter('hashed_code =', hashed_code).get()
        
    def __str__(self):
        return "Team %d: %s"%(self.number, self.name)

    def url(self):
        return reverse(views.team, args=[self.group.slug, self.key().id()])
        
    def members(self):
        """ Returns a list of members """
        return Account.all().filter('teams', self.key())
        
    def send_invites(self):
        secret_code = b64.urlsafe_b64encode(os.urandom(32))
        self.hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        url = APP_URL + reverse(views.connect_account) + '?c=' + secret_code
        mailbody = """
                L.S.
                
                This is an invitation to join a team for the Domination game.
                You've been invited to join %s.
                Use the following link to confirm:
                
                %s
                
                Regards,
                
                Your TA
                """%(str(self), url)
        logging.info(mailbody)
        for email in self.emails:
            mail.send_mail(sender="noreply@%s.appspotmail.com"%get_application_id(),
                           to=email,
                           subject="Invitation to join a team for %s"%(self.group.name),
                           body=mailbody)
        self.put()
        

class Account(db.Model):
    added = db.DateTimeProperty(auto_now_add=True)
    nickname = db.StringProperty()
    teams = db.ListProperty(db.Key)
    
    current_team = None
    
class Brain(db.Model):
    # Performance stats
    score        = db.FloatProperty(default=100.0)
    uncertainty  = db.FloatProperty(default=30.0)
    conservative = db.FloatProperty(default=100.0)
    active       = db.BooleanProperty(default=True)
    games_played = db.IntegerProperty(default=1)
    num_errors   = db.IntegerProperty(default=0)
    # Identity
    group        = db.ReferenceProperty(Group, required=True)
    team         = db.ReferenceProperty(Team, required=True)
    name         = db.StringProperty(default='unnamed')
    version      = db.IntegerProperty(default=1)
    # Timestamps
    added        = db.DateTimeProperty(auto_now_add=True)
    modified     = db.DateTimeProperty(auto_now=True)
    last_active  = db.DateTimeProperty(auto_now_add=True)
    # Code
    code         = db.TextProperty(required=True)
    
    def __str__(self):
        return "v%d %s"%(self.version, self.name)
    
    @classmethod
    def create(cls, team, code, **kwargs):
        team.brain_ver += 1
        team.put()
        kwargs['version'] = team.brain_ver
        kwargs['group'] = team.group
        # Try to extract a name
        namerx = r'NAME *= *[\'\"]([a-zA-Z0-9\-\_ ]+)[\'\"]'
        match = re.search(r'NAME *= *[\'\"]([a-zA-Z0-9\-\_ ]+)[\'\"]', code)
        if match:
            kwargs['name'] = match.groups(1)[0]
            
        return cls(team=team, code=code, **kwargs)
        
    def url(self):
        return reverse(views.brain, args=[self.group.slug, self.key().id()])
        
        
class Game(db.Model):
    added = db.DateTimeProperty(auto_now_add=True)
    group = db.ReferenceProperty(Group, required=True)
    red = db.ReferenceProperty(Brain, collection_name="red_set")
    blue = db.ReferenceProperty(Brain, collection_name="blue_set")
    score_red = db.IntegerProperty()
    score_blue = db.IntegerProperty()
    stats = db.TextProperty()
    log = db.TextProperty()
    winner = db.StringProperty(choices=["red","blue","draw"])
    
    @classmethod
    def play(cls, red_brain, blue_brain, ranked=True):
        """ Play and store a single game. """
        # Dereference the keys
        red_brain = Brain.get(red_brain)
        blue_brain = Brain.get(blue_brain)
        # Run a game
        logging.info("Running game: %s %s vs %s %s"%(red_brain.team, red_brain, blue_brain.team, blue_brain))
        dg = domcore.Game(red_brain_string=red_brain.code,
                          blue_brain_string=blue_brain.code,
                          verbose=False, rendered=False)
        dg.run()
        logging.info("Game done.")
        # Extract stats
        stats = dg.stats
        winner = "red" if stats.score > 0.5 else "blue" if stats.score < 0.5 else "draw"
        # Truncate game log if needed
        log = str(dg.log)
        if len(log) > 16*1024:
            msg = "\n== LOG TRUNCATED ==\n"
            log = log[:16*1024-len(msg)] + msg
        # Adjust agent scores:
        logging.info("Storing game.")
        # Store stuff
        game = cls(red=red_brain, 
                   blue=blue_brain, 
                   stats=repr(dg.stats.__dict__), 
                   winner=winner,
                   log=log, group=red.group)
        game.put()
        logging.info("Game was put.")
