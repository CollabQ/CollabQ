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

from django import http
from django import template
from django.conf import settings
from django.template import loader

from common import api
from common import clean
from common import decorator
from common import exception
from common import util
from common import validate

from install import channels as toinstall

@decorator.gae_admin_required
def install_rootuser(request):
  try:
    root_user = api.actor_get(api.ROOT, settings.ROOT_NICK)
  except:
    root_user = None

  if request.POST:
    site_name = request.POST.get('site_name', None)
    support_channel = request.POST.get('support_channel', None)
    post_name = request.POST.get('post_name', None)
    
    try:
      validate.nonce(request, 'create_root')
      channel = clean.channel(support_channel)
      root_user = api.user_create_root(api.ROOT)
      channel_ref = api.channel_create(api.ROOT, nick=api.ROOT.nick, channel=channel, tags=[],
                                       type='', description='Support Channel')
      
      util.set_metadata('SUPPORT_CHANNEL', support_channel)
      util.set_metadata('SITE_NAME', site_name)
      util.set_metadata('POST_NAME', post_name)

      values = api.init_values(api.ROOT, 'account_type', 'config_values', toinstall.get_account_types())
      values = api.init_values(api.ROOT, 'channel_type', 'config_values', toinstall.get_channel_types())
      
      return util.RedirectFlash('/install', 'Root user created')
    except:
      exception.handle_exception(request)

  redirect_to = '/'

  c = template.RequestContext(request, locals())
  t = loader.get_template('install/templates/rootuser.html')
  return http.HttpResponse(t.render(c))