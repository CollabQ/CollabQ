# Copyright 2010 http://www.collabq.com
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

import sys
import logging

from django import http
from django import template
from django.conf import settings
from django.template import loader
from django.shortcuts import render_to_response

from administration import helper as admin_helper

from common import api
from common import clean
from common import decorator
from common import models
from common import exception
from common import util
from common import validate
from common import views as common_views

ITEMS_BY_PAGE = 20

@decorator.gae_admin_required
def install(request):
  try:
    root_user = api.actor_get(api.ROOT, settings.ROOT_NICK)
    if root_user:
      return util.RedirectFlash('/', 'Already Installed')
  except:
    root_user = None

  post_name = util.get_metadata('POST_NAME')
  default_channel = util.get_metadata('DEFAULT_CHANNEL')

  if request.POST:
    site_name = request.POST.get('site_name', None)
    tagline = request.POST.get('tagline', None)
    post_name = request.POST.get('post_name', None)

    root_mail = request.POST.get('root_mail', None)
    password = request.POST.get('password', None)
    confirm =  request.POST.get('confirm', None)
    default_channel = request.POST.get('default_channel', None)

    try:
      logging.info('saving values')
      validate.nonce(request, 'install')
      validate.email(root_mail)
      validate.password(password)
      validate.password_and_confirm(password, confirm)
      channel = clean.channel(default_channel)

      admin_helper.validate_and_save_sitesettings(site_name, tagline, post_name)
      root_user = api.user_create_root(api.ROOT, password=password)
      api.email_associate(api.ROOT, root_user.nick, root_mail)
      channel_ref = api.channel_create(api.ROOT, nick=api.ROOT.nick, channel=channel, tags=[],
                                       type='', description='Support Channel')
      util.set_metadata('DEFAULT_CHANNEL', default_channel)

      logging.info('Installed and Redirecting to front')
      return util.RedirectFlash('/', 'Installed Successfully')
    except:
      exception.handle_exception(request)

  redirect_to = '/'

  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/install.html', c)

@decorator.gae_admin_required
def admin(request):
  page = 'admin'
  group_menuitem = 'admin'
  title = 'Administration'
  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/admin.html', c)

@decorator.gae_admin_required
def admin_site(request):
  page = 'site'
  title = 'Site Settings'
  
  site_name = util.get_metadata('SITE_NAME')
  tagline = util.get_metadata('TAGLINE')
  post_name = util.get_metadata('POST_NAME')
  
  if request.POST:
    site_name = request.POST.get('site_name', None)
    tagline = request.POST.get('tagline', None)
    post_name = request.POST.get('post_name', None)
    site_description = request.POST.get('site_description', None)
    try:
      validate.nonce(request, 'site')
      admin_helper.validate_and_save_sitesettings(site_name, tagline, post_name, site_description)
    except exception.ValidationError:
      exception.handle_exception(request)

  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/site.html', c)

@decorator.gae_admin_required
def admin_channel(request):
  page = 'channel'
  title = 'Channels Settings'

  enable_channels = util.get_metadata('ENABLE_CHANNELS')
  enable_channel_types = util.get_metadata('ENABLE_CHANNEL_TYPES')
  
  if request.POST:
    enable_channels = request.POST.get('enable_channels', False)
    enable_channel_types = request.POST.get('enable_channel_types', False)
    
    try:
      validate.nonce(request, 'admin_channel')
      validate.bool_checkbox(enable_channels)
      validate.bool_checkbox(enable_channel_types)

      util.set_metadata('ENABLE_CHANNELS', str(enable_channels), 0, {'type':'bool'})
      util.set_metadata('ENABLE_CHANNEL_TYPES', str(enable_channel_types), 0, {'type':'bool'})

    except exception.ValidationError:
      exception.handle_exception(request)
    
  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/channel.html', c)

@decorator.gae_admin_required
def admin_channel_list(request):
  page = 'channel_list'
  title = 'Channels'
  page = util.paging_get_page(request)
  offset = util.paging_get_offset(page, ITEMS_BY_PAGE)
  filter = request.GET.get('filter', 'all')
  
  #owner = api.actor_lookup_nick(request.user, util.get_owner(request))

  new_link = '/admin/channels/new'
  
  size, items = api.admin_get_channels(api.ROOT, ITEMS_BY_PAGE, offset, filter)
  
  start, end, next, prev, first, last = util.paging(page, ITEMS_BY_PAGE, size)
  base_url = '/admin/channels?'
  
  if filter is not None:
    filter_url = '&filter=%s' % filter

  group_menuitem = 'channel'
  menuitem = 'channel-list'

  channel_types = api.get_config_values(api.ROOT, 'channel_type')

  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/channel_list.html', c)

@decorator.gae_admin_required
def admin_channel_new(request):
  page = 'channel_new'
  title = 'Create a Channel'
  
  if request.method == 'POST':
    params = {
              'nick': api.ROOT.nick,
              'channel': request.POST.get('channel'),
              'description': request.POST.get('description', ''),
              'type':request.POST.get('type'),
              'tags': request.POST.getlist('tags[]'),
             }
    channel_ref = api.channel_create(api.ROOT, **params)
    if channel_ref is not None:
      logging.info('Channel created %s' % channel_ref)
      return util.RedirectFlash('/admin/channels', "Channel created successfully")

  group_menuitem = 'channel'
  menuitem = 'channel-new'
  
  channel_types = api.get_config_values(api.ROOT, 'channel_type')

  c = template.RequestContext(request, locals())
  return render_to_response('administration/templates/channel_new.html', c)

@decorator.gae_admin_required
def admin_channel_enable(request, nick):
  logging.info("admin_channel_enable")
  nick = clean.channel(nick)
  
  channel = api.channel_get_safe(api.ROOT, nick)
  channel.enabled = True
  channel.put()
  logging.info("Channel %s" % channel.nick)
  logging.info("Is enabled? %s" % channel.is_enabled())
  
  return util.RedirectFlash('/admin/channels', "Channel has been enabled successfully")

@decorator.gae_admin_required
def admin_channel_disable(request, nick):
  logging.info("admin_channel_disable")
  nick = clean.channel(nick)

  channel = api.channel_get_safe(api.ROOT, nick)
  channel.enabled = False
  channel.put()

  logging.info("Channel %s" % channel.nick)
  logging.info("Is enabled? %s" % channel.is_enabled())

  return util.RedirectFlash('/admin/channels', "Channel has been disabled successfully")

@decorator.gae_admin_required
def admin_auto(request, action):
  page = util.paging_get_page(request)
  offset = util.paging_get_offset(page, ITEMS_BY_PAGE)
  next = str(int(page)+1)
  redirect_url = 'admin/auto/%s?page=%s' % (action, next)

  action = "administration.actions.%s" % action
  __import__(action)
  action_call = sys.modules[action]

  redirect, output = action_call.process(page, ITEMS_BY_PAGE, offset)

  c = template.RequestContext(request, locals())
  t = loader.get_template('administration/templates/auto.html')
  return http.HttpResponse(t.render(c))