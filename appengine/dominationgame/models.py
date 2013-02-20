### Imports ###

# Future imports
from __future__ import with_statement

# Python Imports
import os
import re
import hashlib
import logging
import pickle
import gzip
import base64 as b64
from datetime import datetime, date, time, timedelta

# AppEngine Imports
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext import blobstore
from google.appengine.api import mail
from google.appengine.api import files
from google.appengine.api.app_identity import get_application_id, get_default_version_hostname

# Django Imports
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

# Library Imports
from domination import core as domcore
from domination.scenarios import MatchInfo
import trueskill


### Constants ###
APP_URL = "http://aamasgame.appspot.com"
MAX_ACTIVE_BRAINS = 3
MAX_ERRORS = 10

### Exceptions ###

### Properties ###

class TimeDeltaProperty(db.Property):
    """ Timedelta in seconds, stored as integer """
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
    name   = db.StringProperty(required=True)
    slug   = SlugProperty(name)
    added  = db.DateTimeProperty(auto_now_add=True)
    active = db.BooleanProperty(default=True)
    # Group settings
    gamesettings  = db.TextProperty(default="{}")
    field         = db.TextProperty(default="")
    release_delay = TimeDeltaProperty(default=timedelta(days=5))
    max_uploads   = db.IntegerProperty(default=10)
    
    def __str__(self):
        return self.name
    
    def url(self):
        if self.slug is None:
            self.slug = slugify(self.name)
        return reverse("dominationgame.views.group", args=[self.slug])
        
    def ladder_brains(self):
        q = self.brain_set.filter('active',True)
        return sorted(q, key=lambda b: b.conservative, reverse=True)
        
    def ladder_teams(self):
        return sorted(self.team_set, key=lambda x:x.maxscore, reverse=True)
        
    def recent_games(self):
        return self.game_set.order('-added').fetch(10)
        
    def gamesettings_obj(self):
        try:
            return domcore.Settings(**eval(self.gamesettings))
        except:
            return domcore.Settings()
            
    def field_obj(self):
        if self.field is None:
            return None
        try:
            return domcore.Field.from_string(self.field)
        except:
            return None
    
class Team(db.Model):
    group       = db.ReferenceProperty(Group, required=True)
    name        = db.StringProperty(required=True)
    number      = db.IntegerProperty(default=1)
    hashed_code = db.StringProperty(required=True)
    added       = db.DateTimeProperty(auto_now_add=True)
    emails      = db.StringListProperty()
    # Brains
    brain_ver = db.IntegerProperty(default=0)
    actives   = db.ListProperty(db.Key)
    maxscore  = db.FloatProperty(default=0.0)
    
    @classmethod
    def create(cls, group, **kwargs):
        kwargs['hashed_code'] = b64.urlsafe_b64encode(os.urandom(32))
        kwargs['number'] = group.team_set.count() + 1
        kwargs['parent'] = group
        return cls(group=group, **kwargs)
        
    @classmethod
    def get_by_secret_code(cls, secret_code):
        hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        return cls.all().filter('hashed_code =', hashed_code).get()
        
    def activate(self, brains):
        for brain in self.brain_set:
            brain.active = False
            brain.put()
        for i,brain in enumerate(brains):
            brain.active = True
        self.actives = [b.key() for b in brains]
        def txn():
            db.put(brains)
            self.put()
        db.run_in_transaction(txn)
    
    def send_invites(self, new_emails):
        self.emails = list(set(email.lower() for email in (self.emails + new_emails)))
        secret_code = b64.urlsafe_b64encode(os.urandom(32))
        self.hashed_code = b64.urlsafe_b64encode(hashlib.sha224(secret_code).digest())
        url = APP_URL + reverse("dominationgame.views.connect_account") + '?c=' + secret_code
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
        for email in new_emails:
            mail.send_mail(sender="noreply@%s.appspotmail.com"%get_application_id(),
                           to=email,
                           subject="Invitation to join a team for %s"%(self.group.name),
                           body=mailbody)
        self.put()
        
        
    def __str__(self):
        return "Team %d: %s"%(self.number, self.name)

    def url(self):
        return reverse("dominationgame.views.team", args=[self.group.slug, self.key().id()])
        
    def anchor(self):
        return mark_safe('<a href="%s">%s</a>' % (self.url(), str(self)))
        
    def recent_upload_count(self):
        """ How many brains were uploaded in the last 7 days. """
        recent = datetime.now() - timedelta(days=7)
        return self.brain_set.filter('added >', recent).count(10)
        
    def members(self):
        """ Returns a list of members """
        return Account.all().filter('teams', self.key())
        
    def activebrains(self):
        """ Returns dereferenced active brains """
        return Brain.get(self.actives)
        
    def activebrainkeyids(self):
        """ Returns key.id's for active brains """
        return [str(k.id()) for k in self.actives]
        
    def allbrains(self):
        """ Returns this team's brains, but ordered. """
        return self.brain_set.order('added')
        

class Account(db.Model):
    added = db.DateTimeProperty(auto_now_add=True)
    nickname = db.StringProperty()
    teams = db.ListProperty(db.Key)
    
    current_user = None
    current_team = None

    def short_name(self):
        return self.nickname[:20]


class BrainData(db.Model):
    """ Stores reference to binary data blob for an
        agent brain
    """
    blob     = blobstore.BlobReferenceProperty(required=True)
    filename = db.StringProperty()
    added    = db.DateTimeProperty(auto_now_add=True)
    team     = db.ReferenceProperty(Team, required=True)
    
    @classmethod
    def create(cls, team, datafile):
        file_name = files.blobstore.create(mime_type='application/octet-stream')
        with files.open(file_name, 'a') as f:
            for chunk in datafile.chunks():
                f.write(chunk)
        files.finalize(file_name)
        blob_key = files.blobstore.get_blob_key(file_name)
        braindata = cls(blob=blobstore.BlobInfo.get(blob_key),
                        team=team,
                        filename=datafile.name,
                        parent=team.group)
        braindata.put()
        
    def download_url(self):
        return reverse("dominationgame.views.download_data", args=[self.parent().slug, self.key().id()])
            
class Brain(db.Model):
    # Performance stats
    score        = db.FloatProperty(default=100.0)
    uncertainty  = db.FloatProperty(default=30.0)
    conservative = db.FloatProperty(default=0.0)
    active       = db.BooleanProperty(default=False)
    games_played = db.IntegerProperty(default=0)
    num_errors   = db.IntegerProperty(default=0)
    # Identity
    group   = db.ReferenceProperty(Group, required=True)
    team    = db.ReferenceProperty(Team, required=True)
    name    = db.StringProperty(default='unnamed')
    version = db.IntegerProperty(default=1)
    # Timestamps
    added       = db.DateTimeProperty(auto_now_add=True)
    last_played = db.DateTimeProperty()
    # Source code
    source       = db.TextProperty(required=True)
    data         = db.ReferenceProperty(BrainData)    
    
    def __str__(self):
        return mark_safe("%s v%d"%(self.name[:20], self.version))
        
    def identifier(self):
        return "t%dv%d"%(self.team.number, self.version)
    
    @classmethod
    def create(cls, team, source, **kwargs):
        kwargs['version'] = team.brain_ver + 1
        kwargs['group'] = team.group
        # Try to extract a name
        kwargs['name'] = domcore.Team(source).name_internal
        # Create entity and put
        brain = cls(team=team, source=source, parent=team.group, **kwargs)
        team.brain_ver += 1
        team.put()
        brain.put()
        return brain
        
    def played_game(self, (score, uncertainty), error=False):
        self.score = score
        self.uncertainty = uncertainty
        self.conservative = score - uncertainty
        self.last_played = datetime.now()
        self.games_played += 1
        if error:
            self.num_errors += 1
            if self.num_errors >= MAX_ERRORS:
                self.active = False
        
    def url(self):
        return reverse("dominationgame.views.brain", args=[self.group.slug, self.key().id()])
        
    def download_url(self):
        return reverse("dominationgame.views.brain_download", args=[self.group.slug, self.key().id()])
        
    def blob_anchor(self):
        if self.data and self.data.blob:
            return mark_safe('<a href="%s?fn=%s_blob">Blob</a>'% (self.data.download_url(), self.identifier()))
        else:
            return mark_safe("<span>No Blob</span>")
        
    def anchor(self):
        return mark_safe('<a href="%s">%s</a>' % (self.url(), str(self)))
        
    def games(self):
        """ Returns list of games this brain played """
        rgames = [{'my_score': g.score_red,
                   'opp_score': g.score_blue,
                   'opponent': g.blue,
                   'game': g} for g in self.red_set ]
        bgames = [{'my_score': g.score_blue,
                   'opp_score': g.score_red,
                   'opponent': g.red,
                   'game': g} for g in self.blue_set]
        return sorted(rgames + bgames, key=lambda g: g['game'].added, reverse=True)

        
    def data_reader(self):
        """ Returns a reader into this brains data or None """
        if self.data is not None:
            return self.data.blob.open()
        return None
                
    def release_date(self):
        return self.added + self.group.release_delay
        
    def released(self):
        return self.release_date() < datetime.now()
        
    def owned_by_current_user(self):
        return Account.current_user and (Account.current_user.team == self.team)
        

        
class Game(db.Model):
    added           = db.DateTimeProperty(auto_now_add=True)
    group           = db.ReferenceProperty(Group, required=True)
    red             = db.ReferenceProperty(Brain, collection_name="red_set")
    blue            = db.ReferenceProperty(Brain, collection_name="blue_set")
    score_red       = db.IntegerProperty()
    score_blue      = db.IntegerProperty()
    red_score_diff  = db.FloatProperty()
    blue_score_diff = db.FloatProperty()
    error_red       = db.BooleanProperty(default=False)
    error_blue      = db.BooleanProperty(default=False) 
    stats           = db.TextProperty()
    log             = db.TextProperty()
    replay          = blobstore.BlobReferenceProperty()
    winner          = db.StringProperty(choices=["red","blue","draw"])

    
    @classmethod
    def play(cls, group_key, red_key, blue_key, ranked=True):
        """ Play and store a single game. """
        # Dereference the keys
        red = Brain.get(red_key)
        blue = Brain.get(blue_key)
        group = Group.get(group_key)
        
        # Run a game
        settings = group.gamesettings_obj()
        field = group.field_obj()
        logging.info("Running game: %s %s vs %s %s with %s"%(red.team, red, blue.team, blue, settings))

        # Create the agent_inits
        red_init = {'matchinfo': MatchInfo(1, 1, 0, 1.0)}
        blue_init = {'matchinfo': MatchInfo(1, 1, 0, 1.0)}
        if red.data is not None:
            red_init['blob'] = red.data_reader()
        if blue.data is not None:
            blue_init['blob'] = blue.data_reader()

        # Initialize and run the game
        dg = domcore.Game(red=domcore.Team(red.source + '\n', name=red.identifier(), init_kwargs=red_init),
                          blue=domcore.Team(blue.source + '\n', name=blue.identifier(), init_kwargs=blue_init),
                          settings=settings, field=field,
                          verbose=False, rendered=False, record=True)
        dg.run()
        logging.info("Game done.")
        
        # Extract stats
        stats = dg.stats
        red_score = (red.score, red.uncertainty)
        blue_score = (blue.score, blue.uncertainty)
        # Compute new scores
        if abs(0.5 - stats.score) < trueskill.DRAW_MARGIN:
            winner = "draw"
            red_new, blue_new = trueskill.adjust(red_score, blue_score, draw=True)
        elif stats.score > 0.5:
            winner = "red"
            red_new, blue_new = trueskill.adjust(red_score, blue_score)
        else:
            winner = "blue"
            blue_new, red_new = trueskill.adjust(blue_score, red_score)
            
        # Extract replay & write to blob
        replay = pickle.dumps(dg.replay, pickle.HIGHEST_PROTOCOL)
        blobfile = files.blobstore.create(mime_type='application/gzip')
        with files.open(blobfile, 'a') as f:
            gz = gzip.GzipFile(fileobj=f,mode='wb')
            gz.write(replay)
            gz.close()
            # f.write(replay)
        files.finalize(blobfile)
        replaykey = files.blobstore.get_blob_key(blobfile)
        
        # Truncate game log if needed
        log = dg.log.truncated(kbs=32)
        
        # Adjust agent scores:
        logging.info("Storing game.")
        red.played_game(red_new, error=dg.red.raised_exception)
        blue.played_game(blue_new, error=dg.blue.raised_exception)
        
        # Store stuff
        game = cls(red=red, 
                   blue=blue,
                   score_red=stats.score_red,
                   score_blue=stats.score_blue,
                   error_red=dg.red.raised_exception,
                   error_blue=dg.blue.raised_exception,
                   red_score_diff=red_new[0] - red_score[0],
                   blue_score_diff=blue_new[0] - blue_score[0],
                   stats=repr(dg.stats.__dict__), 
                   winner=winner,
                   replay=replaykey,
                   log=log, 
                   group=group, parent=group)
        def txn():
            # Write the entities
            game.put()
            red.put()
            blue.put()
        db.run_in_transaction(txn)
        logging.info("Game was put.")
        
    def stats_obj(self):
        return eval(self.stats)
        
    def identifier(self):
        date = self.added.strftime("%Y%m%d-%H%M")
        return "%s_%s_vs_%s"%(date, self.red.identifier(), self.blue.identifier())
        
    def url(self):
        return reverse("dominationgame.views.game", args=[self.group.slug, self.key().id()])
        
    def replay_url(self):
        return reverse("dominationgame.views.replay", args=[self.group.slug, self.key().id()])
