import logging

from django import http
from django.conf import settings

from common import api
from common import clean
from common.models import ExternalProfile
from common import memcache
from common import twitter
from common import user
from common import util

def get_nick_from_email(email):
  nick = util.display_nick(email).replace('.', '').replace('_', '')
  view = api.actor_lookup_nick(api.ROOT, nick)

  if view:
    cont = 1
    while view is not None:
      nick_next = nick+str(cont)
      cont+=1
      view = api.actor_lookup_nick(api.ROOT, nick_next)
      if view is None:
        nick = nick_next

  return nick

def reponse_if_exists(id, service=None):
  if service is None:
    view = api.actor_lookup_email(api.ROOT, id)
  else:
    eprofile = api.get_external_profile(service, id)
    if eprofile is not None:
      nick = clean.nick(eprofile.nick)
      view = api.actor_lookup_nick(api.ROOT, nick)
    else:
      return None

  if view:
    response = http.HttpResponseRedirect(view.url('/overview'))
    response = user.set_user_cookie(response, view)
    return response
  
  return None

def user_create(service, params, username='', id='', remote_url=''):
  logging.info("user_create")
  actor_ref = api.user_create(api.ROOT, **params)
  actor_ref.access_level = "delete"

  api.post(actor_ref,
           nick=actor_ref.nick,
           message='Joined %s!' % (util.get_metadata('SITE_NAME')))

  email = params.get('email', None)
  if email is not None:
    api.email_associate(api.ROOT, actor_ref.nick, email)
  else:
    key = 'emailneeded_%s' % util.display_nick(actor_ref.nick)
    memcache.client.set(key, True, 360)

  key = 'firsttime_%s' % util.display_nick(actor_ref.nick)
  memcache.client.set(key, True, 360)

  external_profile_ref = api.create_external_profile(actor_ref.nick, service, username, id, remote_url)

  return actor_ref


def get_full_path(request):
  full_path = ('http', ('', 's')[request.is_secure()], '://',
      request.META['HTTP_HOST'], request.path)
  return ''.join(full_path)

def get_continue_url(request, default_success_url):
  continueUrl = request.GET.get('continue', default_success_url)
  # Sanitize
  if continueUrl.find('//') >= 0 or not continueUrl.startswith('/'):
    continueUrl = default_success_url
  return continueUrl

def twitter_user():
  try:
    token = twitter.get_access_request()
  except:
    return False

  apitwitter = twitter.get_api(token)
  try:
    userinfo = apitwitter.GetUserInfo()
  except:
    logging.info("Error getting user info")
    return False, None

  return userinfo, token