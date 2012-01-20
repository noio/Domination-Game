from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r"^$", "dominationgame.views.frontpage"),
    (r"^login/$", "dominationgame.views.login"),
    (r"^connect/$", "dominationgame.views.connect_account"),
    (r"^groups/$", "dominationgame.views.groups"),
    (r"^([\w\-]+)/$", "dominationgame.views.group"),
    (r"^([\w\-]+)/teams/$", "dominationgame.views.teams"),
)