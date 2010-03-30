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

import re
import logging

from django import http
from django import template
from django.conf import settings
from django.template import loader


from common import api
from common import clean
from common import decorator
from common import display
from common import exception
from common import twitter
from common import user
from common import util
from common import views as common_views

ENTRIES_PER_PAGE = 20
CONTACTS_PER_PAGE = 15
CHANNELS_PER_PAGE = 9

tag_re = re.compile(r'^(?P<tag>[a-zA-Z0-9]{%d,%d})$'
    % (clean.NICK_MIN_LENGTH, clean.NICK_MAX_LENGTH))
hashtag_re = re.compile(r'^#(?P<tag>[a-zA-Z][a-zA-Z0-9]{%d,%d})$'
    % (clean.NICK_MIN_LENGTH, clean.NICK_MAX_LENGTH))
    
def hashtag_search(request, tag=''):
  view = request.user

  page = util.paging_get_page(request)

  if view is not None:
    unauth = twitter.is_unauth(request)
    twitter_options = twitter.twitter_options(request)
    if 'twitter' in request.POST:
      if unauth:
        return http.HttpResponseRedirect('/twitter/auth?redirect_to=/%s/overview' % view.display_nick())
      status = twitter.post_update(request)
      if status:
        flasherror = ["We have experimented some problems trying to post a cc in twitter"]

    handled = common_views.handle_view_action(
        request,
        {
          'entry_remove': request.path,
          'entry_remove_comment': request.path,
          'entry_mark_as_spam': request.path,
          'presence_set': request.path,
          'settings_hide_comments': request.path,
          'post': '/%s/overview' % view.display_nick(),
        }
    )
    logging.info('handled: %s' % handled)
    if handled:
      return handled

  q = request.GET.get('q', None)
  if q is not None:
    result = hashtag_re.search(q)
    if result:
      tag = result.groupdict()['tag']
    else:
      tag = q
    
  hashtag_match = tag_re.search(tag)
  if hashtag_match:
    match_dict = hashtag_match.groupdict()
    tag = '#'+match_dict['tag'].lower()

    limit = ENTRIES_PER_PAGE+ENTRIES_PER_PAGE*(page-1)
    more, relations = api.hashtag_get_relations( request.user, tag, limit)
    entries = api.hashtag_get_entries(request.user, [relation.uuid for relation in relations])
    entries = api.entry_get_entries(request.user, [entry.key().name() for entry in entries])

    stream_keys = [e.stream for e in entries]
    try:
      actor_streams = api.stream_get_actor(request.user, view.nick)
    except exception.ApiException:
      actor_streams = []
    except:
      actor_streams = []
      
    stream_keys += [s.key().name() for s in actor_streams]
    streams = api.stream_get_streams(request.user, stream_keys)

    try:
      contact_nicks = api.actor_get_contacts(request.user,
                                           view.nick,
                                           limit=CONTACTS_PER_PAGE)
    except exception.ApiException:
      contact_nicks = []
    except:
      contact_nicks = []

    actor_nicks = (contact_nicks +
                   [s.owner for s in streams.values()] +
                   [e.owner for e in entries] +
                   [e.actor for e in entries])
                   
    actors = api.actor_get_actors(request.user, actor_nicks)

    contacts = [actors[x] for x in contact_nicks if actors[x]]
    streams = display.prep_stream_dict(streams, actors)
    entries = display.prep_entry_list(entries, streams, actors)
    if more:
      last = entries[len(entries)-1].uuid
  else:
    entries = []

    try:
      contact_nicks = api.actor_get_contacts(request.user,
                                           view.nick,
                                           limit=CONTACTS_PER_PAGE)
    except exception.ApiException:
      contact_nicks 

    actor_nicks = (contact_nicks)
    actors = api.actor_get_actors(request.user, actor_nicks)
    contacts = [actors[x] for x in contact_nicks if actors[x]]

  is_owner = True
  if view is not None:
    channels_count = view.extra.get('channel_count', 0)
    channels_more = channels_count > CHANNELS_PER_PAGE
    followers_count = view.extra.get('follower_count', 0)
    contacts_count = view.extra.get('contact_count', 0)
  
    channels = api.actor_get_channels_member(request.user, view.nick,
                                limit=(CHANNELS_PER_PAGE + 1))
    templatebase = 'common/templates/base_sidebar.html'

  else:
    templatebase = 'common/templates/base_single.html'

  green_top = True
  sidebar_green_top = True
  next = page+1
  actor_link = True

  c = template.RequestContext(request, locals())
  t = loader.get_template('hashtag/templates/hashtag_search.html')

  return http.HttpResponse(t.render(c))
