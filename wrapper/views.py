import logging

import simplejson

from django import http
from django import template
from django.template import loader
from django.conf import settings

from common import api
from common import decorator
from common import validate
from common import util

#ACCOUNT
@decorator.authentication_required
@decorator.login_required
def verify_credentials(request, format='html'):
  logging.info("verify_credentials")
  view = request.user
  
  presence_stream = api.stream_get_presence(request.user, view.nick)
  last_entry = api.entry_get_last(request.user, presence_stream.keyname())

  validate.format_page(format)
  
  template_file = 'wrapper/templates/account/verify_credentials.%s' % format
  t = loader.get_template(template_file)
  c = template.RequestContext(request, locals())

  if format == 'html':
    return http.HttpResponse(t.render(c))
  if format == 'xml':
    return http.HttpResponse(t.render(c))
  elif format == 'json':
    return util.HttpJsonResponse(t.render(c), request)


#Statuses
def statuses_show(request, entry_id, format='html'):
  logging.info("statuses_show")
  try:
    entry = api.entry_get_uuid(request.user, entry_id)
  except:
    entry = api.entry_get_uuid(None, entry_id)

  if entry.entry:
    try:
      entry_owner = api.entry_get_safe(request.user, entry.entry)
    except:
      entry_owner = api.entry_get_safe(None, entry.entry)
    owner = api.actor_get_safe(entry_owner.owner)
  validate.format_page(format)

  created_at = entry.created_at.strftime('%a %b %d %H:%M:%S +0000 %Y')
  
  logging.info("created_at: %s" % created_at)
  
  template_file =  "wrapper/templates/statuses/show.%s" % format
  c = template.RequestContext(request, locals())
  t = loader.get_template(template_file)
  
  if format == 'html':
    return http.HttpResponse(t.render(c))
  if format == 'xml':
    return http.HttpResponse(t.render(c))
  elif format == 'json':
    return util.HttpJsonResponse(t.render(c), request)