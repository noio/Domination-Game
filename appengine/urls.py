from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r"^$", "dominationgame.views.frontpage"),
    (r"^groups/$", "dominationgame.views.groups"),
    (r"^login/$", "dominationgame.views.login"),
    (r"^connect/$", "dominationgame.views.connect_account"),
    (r"^(?P<groupslug>[\w\-]+)/$", "dominationgame.views.group"),
    (r"^(?P<groupslug>[\w\-]+)/teams/$", "dominationgame.views.teams"),
    (r"^(?P<groupslug>[\w\-]+)/dashboard/$", "dominationgame.views.dashboard"),
)