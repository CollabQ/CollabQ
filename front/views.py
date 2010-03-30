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
import random

from django.conf import settings
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect

from common import exception
from common import user
from common.models import Actor

from common import api, util
from common.display import prep_stream_dict, prep_entry_list

ENTRIES_PER_PAGE = 5
SIDEBAR_LIMIT = 9
SIDEBAR_FETCH_LIMIT = 50
FRONT_MEMBERS = 9

def front_front(request):
  logging.info("In the Frontpage")
  # if the user is logged in take them to their overview
  if request.user:
    url = request.user.url(request=request)
    return HttpResponseRedirect(url + "/overview")

  # NOTE: grab a bunch of extra so that we don't ever end up with
  #       less than 5
  per_page = ENTRIES_PER_PAGE * 2

  inbox = api.inbox_get_explore(request.user, limit=per_page)

  featured_members = api.actor_get_random_actors(api.ROOT, FRONT_MEMBERS)
  random.shuffle(featured_members)

  root = api.ROOT

  area = 'frontpage'

  t = loader.get_template('front/templates/front.html')
  c = RequestContext(request, locals())

  return HttpResponse(t.render(c));
