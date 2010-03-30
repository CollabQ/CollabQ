# Copyright 2010 http://www.collabq.com
import logging

from django.conf import settings
from django.http import HttpResponseRedirect

from common import api
from common import exception

class VerifyInstallMiddleware(object):
  def process_request(self, request):
    logging.info("VerifyInstallMiddleware")
    logging.info("Path %s" % request.path)
    if not request.path == '/install':
      try:
        root_user = api.actor_get(api.ROOT, settings.ROOT_NICK)
        logging.info("Root Exists")
      except:
        logging.info("Root Does Not Exists")
        return HttpResponseRedirect('/install')