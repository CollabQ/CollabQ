import logging
import openidgae

from django import http
from django import template
from django.template import loader
from django.conf import settings
from django.core import urlresolvers
#from django.utils.decorators import decorator_from_middleware
#from facebook.djangofb import FacebookMiddleware

from openid.consumer.consumer import Consumer
from openid.consumer import discover
from openidgae import store

from common import api
from common import memcache
from common import twitter
from common import user
from common import util
from poboxopenid import util as util_externals

import facebook.djangofb as facebook

def openid_google(request):
  openid = 'https://www.google.com/accounts/o8/id'
  return openid_login(request, openid)

def openid_login(request, openid='https://www.google.com/accounts/o8/id'):
  logging.info('google_login')
  openid = openid.strip()
  if not openid:
    message='Not open id'

  c = Consumer({},store.DatastoreStore())
  try:
    auth_request = c.begin(openid)
  except discover.DiscoveryFailure, e:
    logging.error('OpenID discovery error with begin on %s: %s'
        % (openid, str(e)))
    message = 'An error occured determining your server information.  Please try again.'

  from openid.extensions import sreg
  sreg_request = sreg.SRegRequest(
      optional=['dob', 'gender', 'postcode'],
      required=['email', 'nickname', 'fullname', 'country', 'language', 'timezone'])
  auth_request.addExtension(sreg_request)

  from openid.extensions import ax
  ax_req = ax.FetchRequest()
  ax_req.add(ax.AttrInfo('http://schema.openid.net/contact/email',
        alias='email',required=True))
  ax_req.add(ax.AttrInfo('http://axschema.org/namePerson/first',
        alias='firstname',required=True))
  ax_req.add(ax.AttrInfo('http://axschema.org/namePerson/last',
        alias='lastname',required=True))
  ax_req.add(ax.AttrInfo('http://axschema.org/pref/language',
        alias='language',required=True))
  ax_req.add(ax.AttrInfo('http://axschema.org/contact/country/home',
        alias='country',required=True))
  auth_request.addExtension(ax_req)

  import urlparse
  parts = list(urlparse.urlparse(util_externals.get_full_path(request)))
  # finish URL with the leading "/" character removed
  parts[2] = urlresolvers.reverse('openidgae.views.OpenIDFinish')[1:]

  continueUrl = util_externals.get_continue_url(request, '/openid/processuser')
  import urllib
  parts[4] = 'continue=%s' % urllib.quote_plus(continueUrl)
  parts[5] = ''
  return_to = urlparse.urlunparse(parts)

  realm = urlparse.urlunparse(parts[0:2] + [''] * 4)

  # save the session stuff
  response = http.HttpResponse()
  session = openidgae.get_session(request, response)
  import pickle
  session.openid_stuff = pickle.dumps(c.session)
  session.put()

  # send the redirect!  we use a meta because appengine bombs out
  # sometimes with long redirect urls
  redirect_url = auth_request.redirectURL(realm, return_to)
  response.write(
      "<html><head><meta http-equiv=\"refresh\" content=\"0;url=%s\"></head><body></body></html>"
      % (redirect_url,))
  return response

def openid_createuser(request):
  person = openidgae.get_current_person(request, http.HttpResponse())
  email = person.get_email()

  res = util_externals.reponse_if_exists(email)
  if res is not None:
    return res

  nick = util_externals.get_nick_from_email(email)
  
  params = {
    'nick': nick,
    'password': util.generate_password(),
    'first_name': person.get_field_value('firstname', 'none'),
    'last_name': person.get_field_value('lastname', 'none'),
    'fromopenid': True,
    'email':email,
  }
  
  actor_ref = util_externals.user_create('google', params, util.display_nick(email), email)
  
  # NOTE: does not provide a flash message
  response = util.RedirectFlash('/', 'Welcome to %s' % util.get_metadata('SITE_NAME'))
  user.set_user_cookie(response, actor_ref)
  return response

def twitter_user_create(request):
  twitter_user, token = util_externals.twitter_user()

  if not twitter_user:
    c = template.RequestContext(request, locals())
    t = loader.get_template('poboxopenid/templates/twitter_login.html')
    return http.HttpResponse(t.render(c))

  res = util_externals.reponse_if_exists(twitter_user.id, 'twitter')
  if res is not None:
    return res

  nick = util_externals.get_nick_from_email(twitter_user.screen_name)
  
  params = {
    'nick': nick,
    'password': util.generate_password(),
    'first_name': twitter_user.name,
    'last_name': '',
    'fromopenid': True,
    'email':None,
  }

  actor_ref = util_externals.user_create('twitter', 
                              params,
                              twitter_user.screen_name,
                              str(twitter_user.id),
                              'http://twitter.com/%s'%twitter_user.screen_name)
                                          
  logging.info("Storing twitter_access_token after create a user")
  actor_ref.extra['twitter_access_token'] = token
  actor_ref.put()
  
  response = util.RedirectFlash('/', 'Welcome to P.O.BoxPress')
  user.set_user_cookie(response, actor_ref)
  return response

#@decorator_from_middleware(FacebookMiddleware)
#@facebook.require_login('/facebook/signin', False)
#def facebook_processuser(request):
#  c = template.RequestContext(request, locals())
#  t = loader.get_template('poboxopenid/templates/facebook_login.html')
#  return http.HttpResponse(t.render(c))


#@decorator_from_middleware(FacebookMiddleware)
#@facebook.require_login('/facebook/signin', False)
#def facebook_canvas(request):
#  values = request.facebook.users.getInfo([request.facebook.uid], ['first_name', 'is_app_user', 'has_added_app'])[0]
#
#  name, is_app_user, has_added_app = values['first_name'], values['is_app_user'], values['has_added_app']
#
#  if has_added_app == '0':
#    return request.facebook.redirect(request.facebook.get_add_url())
#
#  c = template.RequestContext(request, locals())
#  t = loader.get_template('poboxopenid/templates/canvas.fbml')
#  return http.HttpResponse(t.render(c))