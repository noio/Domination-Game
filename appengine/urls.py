from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r"^$", "dominationgame.views.frontpage"),
    (r"^edit_groups/$", "dominationgame.views.edit_groups"),
    (r"^login/$", "dominationgame.views.login"),
    (r"^connect/$", "dominationgame.views.connect_account"),
    (r"^tasks/laddermatch/$", "dominationgame.views.laddermatch"),
    (r"^(?P<groupslug>[\w\-]+)/$", "dominationgame.views.group"),
    (r"^(?P<groupslug>[\w\-]+)/dashboard/$", "dominationgame.views.dashboard"),
    (r"^(?P<groupslug>[\w\-]+)/brain/(?P<brain_id>\d+)/$", "dominationgame.views.brain"),
    (r"^(?P<groupslug>[\w\-]+)/team/(?P<team_id>\d+)$", "dominationgame.views.team"),
    (r"^(?P<groupslug>[\w\-]+)/edit_teams/$", "dominationgame.views.edit_teams"),
)