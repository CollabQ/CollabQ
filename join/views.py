# Copyright 2010 http://www.collabq.com
# Copyright 2009 Google Inc.
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
import openidgae

from django import http
from django import template
from django.conf import settings
from django.template import loader
import simplejson

from common.display import prep_stream_dict, prep_entry_list, prep_entry, prep_comment_list, DEFAULT_AVATARS

from common import api
from common import component
from common import exception
from common import decorator
from common import display
from common import google_contacts
from common import mail
from common import memcache
from common import oauth_util
from common import user
from common import util
from common import validate
from common import views as common_views


def join_join(request):
  if request.user:
    raise exception.AlreadyLoggedInException()

  redirect_to = request.REQUEST.get('redirect_to', '/')

  account_types = api.get_config_values(api.ROOT, 'account_type')

  # get the submitted vars
  nick = request.REQUEST.get('nick', '');
  first_name = request.REQUEST.get('first_name', '');
  last_name = request.REQUEST.get('last_name', '');
  email = request.REQUEST.get('email', '');
  password = request.REQUEST.get('password', '');
  confirm = request.REQUEST.get('confirm', '');
  hide = request.REQUEST.get('hide', '');
  country_tag = request.REQUEST.get('country_tag', '')

  if request.POST:
    try:
      # TODO validate
      params = util.query_dict_to_keywords(request.POST)

      if hide:
        params['privacy'] = 2

      # XXX: Check if the data come from a openid account
      # @author: josem@prosoftpeople.com
      fromopenid = request.POST.get('fromopenid', False) and True
      if fromopenid:
        try:
          person = openidgae.get_current_person(request, http.HttpResponse())
        except:
          raise exception.ServiceError
        
        email = person.get_email()
        if email == params['email']:
          params['password'] = util.generate_password()
        else:
          raise exception.ServiceError

      # ENDXXX

      validate.email(email)
      if not mail.is_allowed_to_send_email_to(email):
        raise exception.ValidationError("Cannot send email to that address")

      # TODO start transaction
      if api.actor_lookup_email(api.ROOT, email):
        raise exception.ValidationError(
            'That email address is already associated with a member.')
      
      actor_ref = api.user_create(api.ROOT, **params)
      actor_ref.access_level = "delete"

      api.post(actor_ref, 
               nick=actor_ref.nick, 
               message='Joined %s!' % (util.get_metadata('SITE_NAME')),
               icon='jaiku-new-user')
      if fromopenid:
        api.email_associate(api.ROOT, actor_ref.nick, email)
      else:
        # send off email confirmation
        api.activation_request_email(actor_ref, actor_ref.nick, email)

      logging.info('setting firsttime_%s from register page' % actor_ref.nick)
      memcache.client.set('firsttime_%s' % nick, True)
      # TODO end transaction
      welcome_url = util.qsa('/', {'redirect_to': redirect_to})

      # NOTE: does not provide a flash message
      response = http.HttpResponseRedirect(welcome_url)
      user.set_user_cookie(response, actor_ref)
      return response
    except:
      exception.handle_exception(request)

  # for legal section
  legal_component = component.include('legal', 'dummy_legal')
  legal_html = legal_component.embed_join()
  
  # for sidebar
  sidebar_green_top = True

  area = "join"
  c = template.RequestContext(request, locals())

  t = loader.get_template('join/templates/join.html')
  return http.HttpResponse(t.render(c))

@decorator.login_required
def join_welcome(request):
  redirect_to = request.REQUEST.get('redirect_to', '/')
  next = '/welcome/1'

  view = request.user
  page = 'start'

  area = 'welcome'
  c = template.RequestContext(request, locals())
  
  t = loader.get_template('join/templates/welcome_%s.html' % page)
  return http.HttpResponse(t.render(c))

@decorator.login_required
def join_welcome_photo(request):
  #@begin zero code
  #next = '/welcome/2'
  next = '/welcome/done'
  #@end
  redirect_to = request.REQUEST.get('redirect_to', '/')

  # Welcome pages have a 'Continue' button that should always lead
  # to the next page. 
  success = '/welcome/1'
  if 'continue' in request.POST:
    success = next

  rv = common_views.common_photo_upload(
    request, 
    util.qsa(success, {'redirect_to': redirect_to})
    )
  if rv:
    return rv

  # If avatar wasn't changed, just go to next page, if 'Continue' was clicked.
  if 'continue' in request.POST:
    return http.HttpResponseRedirect(util.qsa(next, {'redirect_to': redirect_to}))
  
  avatars = display.DEFAULT_AVATARS

  view = request.user
  page = 'photo'
  area = 'welcome-pobox'
  c = template.RequestContext(request, locals())

  t = loader.get_template('join/templates/welcome_%s.html' % page)
  return http.HttpResponse(t.render(c))

@decorator.login_required
def join_welcome_mobile(request):
  redirect_to = request.REQUEST.get('redirect_to', '/')
  next = '/welcome/3'
  

  try:
    if not settings.SMS_ENABLED:
      raise exception.FeatureDisabledError('Mobile activation is currently disabled')
    
  except:
    exception.handle_exception(request)
  
  mobile = api.mobile_get_actor(request.user, request.user.nick)

  # set the progress
  welcome_photo = True

  view = request.user
  page = 'mobile'

  area = 'welcome'
  c = template.RequestContext(request, locals())
  
  t = loader.get_template('join/templates/welcome_%s.html' % page)
  return http.HttpResponse(t.render(c))

def join_welcome_done(request):
  redirect_to = request.REQUEST.get('redirect_to', '/')

  # set the progress
  welcome_photo = True
  welcome_mobile = True
  welcome_contacts = True

  view = request.user
  page = 'done'

  area = 'welcome-pobox'
  c = template.RequestContext(request, locals())
  
  t = loader.get_template('join/templates/welcome_%s.html' % page)
  return http.HttpResponse(t.render(c))
