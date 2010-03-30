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

from django import http
from django import template
from django.conf import settings
from django.template import loader

from common import api, helper, util
from common import twitter
from common import views as common_views
from common.display import prep_entry_list, prep_stream_dict

ENTRIES_PER_PAGE = 20
CONTACTS_PER_PAGE = 15
CHANNELS_PER_PAGE = 4

def explore_recent(request, format="html"):
  if request.user:
    view = request.user
    logging.info("entering here")
    #twitter
    unauth = twitter.is_unauth(request)
    if 'twitter' in request.POST:
      if unauth:
        return http.HttpResponseRedirect('/twitter/auth?redirect_to=/')
      status = twitter.post_update(request)
      if status:
        flasherror = ["We have experimented some problems trying to post a cc in twitter"]
        
    handled = common_views.handle_view_action(
        request,
        { 'entry_remove': request.path,
          'entry_remove_comment': request.path,
          'entry_mark_as_spam': request.path,
          'actor_add_contact': request.path,
          'actor_remove_contact': request.path,
          'post': request.path,
          'presence_set': request.path,
        }
    )
    if handled:
      return handled

  subtab = 'explore'
  per_page = ENTRIES_PER_PAGE
  offset, prev = util.page_offset(request)

  inbox = api.inbox_get_explore(request, limit=(per_page + 1),
                                offset=offset)

  entries, more = helper.get_inbox_entries(request, inbox)
  stream_keys = [e.stream for e in entries]
  streams = api.stream_get_streams(request.user, stream_keys)
  actor_nicks = [e.owner for e in entries] + [e.actor for e in entries]
  actors = api.actor_get_actors(request.user, actor_nicks)
                                              
  # here comes lots of munging data into shape
  entries = prep_entry_list(entries, streams, actors)

  if request.user:
    channels_count = view.extra.get('channel_count', 0)
    channels_more = channels_count > CHANNELS_PER_PAGE
    followers_count = view.extra.get('follower_count', 0)
    contacts_count = view.extra.get('contact_count', 0)
    contacts_more = contacts_count > CONTACTS_PER_PAGE
    contact_nicks = api.actor_get_contacts_safe(request.user,
                                              view.nick,
                                              limit=CONTACTS_PER_PAGE)
    contacts = api.actor_get_actors(request.user, contact_nicks)
    contacts = [contacts[x] for x in contact_nicks if contacts[x]]

    green_top = True
    sidebar_green_top = True
  # END inbox generation chaos

  area = 'explore'
  actor_link = True
  
  c = template.RequestContext(request, locals())

  if format == 'html':
    t = loader.get_template('explore/templates/recent.html')
    return http.HttpResponse(t.render(c));
  elif format == 'json':
    t = loader.get_template('explore/templates/recent.json')
    r = util.HttpJsonResponse(t.render(c), request)
    return r
  elif format == 'atom':
    t = loader.get_template('explore/templates/recent.atom')
    r = util.HttpAtomResponse(t.render(c), request)
    return r
  elif format == 'rss':
    t = loader.get_template('explore/templates/recent.rss')
    r = util.HttpRssResponse(t.render(c), request)
    return r
