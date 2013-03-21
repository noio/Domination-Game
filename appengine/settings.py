"""Minimal Django settings."""

import os

APPEND_SLASH = True
DEBUG = True
INSTALLED_APPS = ('dominationgame',)
ROOT_PATH = os.path.dirname(__file__)
ROOT_URLCONF = 'urls'
MIDDLEWARE_CLASSES = (
    #'google.appengine.ext.appstats.recording.AppStatsDjangoMiddleware',
    #'firepython.middleware.FirePythonDjango',
    #'appstats.recording.AppStatsDjangoMiddleware',
    'django.middleware.common.CommonMiddleware',
    'dominationgame.middleware.AddUserToRequestMiddleware',
    'dominationgame.middleware.ScopeToGroupMiddleware',
    #'django.middleware.http.ConditionalGetMiddleware',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
)

# only use the memory file uploader, do not use the file system - not able to do so on
# google app engine
FILE_UPLOAD_HANDLERS = ('django.core.files.uploadhandler.MemoryFileUploadHandler',)
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024*1024*10 # the django default: 2.5MB

TEMPLATE_STRING_IF_INVALID = 'err{{%s}}' if DEBUG else ''
TEMPLATE_DEBUG = DEBUG
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates'),
)
MEDIA_URL = '/static/'

