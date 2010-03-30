# Copyright 2010 http://www.collabq.com
# Copyright P.O.BoxPress.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import urllib2
import simplejson

from common import memcache
from common import util
from django.conf import settings
from oauth import oauth
from twitterapi import oauthtwitter

from google.appengine.api import urlfetch

def is_unauth(request):
  if request.user is None:
    return True
  return request.user.extra.get('twitter_access_token', None) is None

def get_access_token(request):
  if request.user is not None:
    return request.user.extra.get('twitter_access_token', False)
  return False

def twitter_options(request):
  if is_unauth(request):
    return {'cc_twitter':False}
  return request.user.extra.get('twitter_settings', {'cc_twitter':True})

def get_request_token():
  twitter = oauthtwitter.OAuthApi(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
  logging.info("Request Token")

  request_token = twitter.getRequestToken()

  return twitter, request_token

def get_authorization_url(redirect = None):
  logging.info("Authorization URL")
  
  if redirect is not None:
    memcache.client.set('redirect_to', redirect, 1200)

  twitter, request_token = get_request_token()
  memcache.client.set('request_token',request_token.to_string(), 1200)
  authorization_url = twitter.getAuthorizationURL(request_token)
  
  return authorization_url

def get_signin_url(redirect_to = '/'):
  logging.info("get_signin_url - redirect_to: %s" % redirect_to)
  memcache.client.set('redirect_to', redirect_to, 1200)
  twitter, request_token = get_request_token()
  memcache.client.set('request_token',request_token.to_string(), 1200)
  signin_url = twitter.getSigninURL(request_token)

  return signin_url

def get_access_request():
  logging.info("Access Token")
  token = memcache.client.get('request_token')
  memcache.client.delete('request_token')

  request_token = oauth.OAuthToken.from_string(token)
  twitter       = oauthtwitter.OAuthApi(settings.TWITTER_CONSUMER_KEY,
                                        settings.TWITTER_CONSUMER_SECRET,
                                        request_token)
  logging.info("Access Token")
  access_token = twitter.getAccessToken()

  return access_token

def get_api(access_token):
  twitter = oauthtwitter.OAuthApi(settings.TWITTER_CONSUMER_KEY,
                                       settings.TWITTER_CONSUMER_SECRET,
                                       access_token)
  return twitter

def twitter_get_entries(request, count):
  access_token = get_access_token(request)
  api_twitter = get_api(access_token)
  user_info = api_twitter.GetUserInfo()
  return user_info, api_twitter.GetFriendsTimeline(user_info.screen_name, count)

def twitter_search(request, q, page=None, since_id=None, show_user=True, lang=None, url='http://search.twitter.com/search.json'):
  params = {}
  if page is not None:
    params['page'] = page
  if since_id is not None:
    params['since_id'] = since_id
  if show_user is not None:
    params['show_user'] = show_user
  if lang is not None:
    params['lang'] = lang
  _url = util.qsa('%s?q=%s' % (url, q), params)
  logging.info('_url: %s'%_url)
  
  result = urlfetch.fetch(_url)
  if result.status_code == 200:
    data = simplejson.loads(result.content).get('results')
  else:
    logging.info("Problems with twitter connection")
    raise Exception('Problems with twitter connection')
  
  return data

def post_update(request):
  access_token = get_access_token(request)
  api_twitter = get_api(access_token)
  message = request.POST.get('message')
  if len(message) > (settings.MAX_TWITTER_LENGTH-1):
    max_length = settings.MAX_TWITTER_LENGTH-4
    message = message[:max_length]+'...'
  try:
    success = api_twitter.PostUpdate(message.encode('utf-8'))
  except urllib2.HTTPError:
    logging.error("HTTP Error")
    success = False
  except Exception:
    logging.error("Exception")
    success = False
  return success