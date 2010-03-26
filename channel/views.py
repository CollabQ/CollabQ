import logging
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

from django import http
from django import template
from django.conf import settings
from django.template import loader
from common.component import logging

import settings

from common import api
from common import clean
from common import decorator
from common import display
from common import exception
from common import normalize
from common import twitter
from common import user
from common import util
from common import validate
from common import views as common_views

from channel import helper as channel_helper

ENTRIES_PER_PAGE = 20
CHANNEL_HISTORY_PER_PAGE = 20
CHANNELS_PER_INDEX_PAGE = 12
CHANNELS_PER_PAGE = 10
CONTACTS_PER_PAGE = 24
CHANNELS_SIDEBAR = 24

def channel_create(request, format='html'):
  if not util.get_metadata('ENABLE_CHANNELS'):
    raise exception.AdminRequiredError
  
  channel = request.REQUEST.get('channel', '')

  handled = common_views.handle_view_action(
      request,
      {'channel_create': '/channel/%s' % channel,
       }
      )
  if handled:
    return handled

  # for template sidebar
  sidebar_green_top = True

  area = 'channel'
  c = template.RequestContext(request, locals())

  if format == 'html':
    t = loader.get_template('channel/templates/create.html')
    return http.HttpResponse(t.render(c))


def channel_index(request, format='html'):
  """ the index page for channels, /channel

  should list the channels you administer, the channels you belong to
  and let you create new channels

  if you are not logged in, it should suggest that you log in to create or
  join channels and give a list of public channels
  """
  if not request.user:
    return channel_index_signedout(request, format='html')

  owned_nicks = api.actor_get_channels_admin(
      request.user,
      request.user.nick,
      limit=(CHANNELS_PER_INDEX_PAGE + 1))
  owned_more = len(owned_nicks) > CHANNELS_PER_INDEX_PAGE

  followed_nicks = api.actor_get_channels_member(
      request.user,
      request.user.nick,
      limit=(CHANNELS_PER_INDEX_PAGE + 1))
  followed_more = len(owned_nicks) > CHANNELS_PER_INDEX_PAGE

  channel_nicks = owned_nicks + followed_nicks
  channels = api.channel_get_channels(request.user, channel_nicks)

  owned_channels = [channels[x] for x in owned_nicks if channels[x]]
  for c in owned_channels:
    c.i_am_admin = True

  followed_channels = [
      channels[x] for x in followed_nicks 
          if channels[x] and x not in owned_nicks
  ]
  for c in followed_channels:
    c.i_am_member = True

  try:
    # for the Our Picks section of the sidebar
    ourpicks_channels = api.actor_get_channels_member(request.user, api.ROOT.nick)
    ourpicks_channels = api.channel_get_channels(request.user, ourpicks_channels)  
    ourpicks_channels = [x for x in ourpicks_channels.values() if x]
  except exception.ApiNotFound:
    pass
  
  related_tags = api.channel_get_children_tags(request.user)

  is_admin_user = request.user.nick in settings.ADMINS_POBOX
  
  area = 'channel'
  c = template.RequestContext(request, locals())
  

  if format == 'html':
    t = loader.get_template('channel/templates/index.html')
    return http.HttpResponse(t.render(c))


def channel_index_signedout(request, format='html'):
  area = 'channel'
  c = template.RequestContext(request, locals())

  if format == 'html':
    t = loader.get_template('channel/templates/index_signedout.html')
    return http.HttpResponse(t.render(c))


def channel_history(request, nick, format='html'):
  """ the page for a channel

  if the channel does not exist we go to create channel instead

  should let you join a channel or post to it if you already are a member
  also leave it if you are a member,
  display the posts to this channel and the member list if you are allowed
  to see them

  if you are an admin you should have the options to modify the channel
  """
  tag = nick
  nick = clean.channel(nick)

  view = api.channel_get_safe(request.user, nick)
  if not view:
    return http.HttpResponseRedirect('/hashtag/%s' % tag)

  if not view.is_enabled():
    return http.HttpResponseRedirect('/hashtag/%s' % tag)

  admins = api.channel_get_admins(request.user, channel=view.nick)
  members = api.channel_get_members(request.user, channel=view.nick)

  unauth = twitter.is_unauth(request)
  if 'twitter' in request.POST:
    if unauth:
      return http.HttpResponseRedirect('/twitter/auth?redirect_to=/channel/%s/twitter/' % _nick)
    success = twitter.post_update(request)

    
  handled = common_views.handle_view_action(
      request,
      {'channel_join': request.path,
       'channel_part': request.path,
       'channel_post': request.path,
       'entry_remove': request.path,
       'entry_remove_comment': request.path,
       'entry_mark_as_spam': request.path,
       'subscription_remove': request.path,
       'subscription_request': request.path,
       }
      )
  if handled:
    return handled

  privacy = 'public'

  user_can_post, user_is_admin = _user_permissions(request, view)

  if user_can_post:
    privacy = 'contacts'
    if user_is_admin:
      privacy = 'private'

  per_page = CHANNEL_HISTORY_PER_PAGE
  offset, prev = util.page_offset(request)

  if privacy == 'public':
    inbox = api.inbox_get_actor_public(
        request.user,
        view.nick,
        limit=(per_page + 1),
        offset=offset)
  elif privacy == 'contacts':
    inbox = api.inbox_get_actor_contacts(
        request.user,
        view.nick,
        limit=(per_page + 1),
        offset=offset)
  elif privacy == 'private':
    inbox = api.inbox_get_actor_private(
        api.ROOT,
        view.nick,
        limit=(per_page + 1),
        offset=offset)

  # START inbox generation chaos
  # TODO(termie): refacccttttooorrrrr

  entries = api.entry_get_entries(request.user, inbox)
  # clear out deleted entries
  per_page = per_page - (len(inbox) - len(entries))
  entries, more = util.page_entries(request, entries, per_page)

  stream_keys = [e.stream for e in entries]
  actor_streams = api.stream_get_actor(request.user, view.nick)
  stream_keys += [s.key().name() for s in actor_streams]
  streams = api.stream_get_streams(request.user, stream_keys)

  contact_nicks = api.actor_get_contacts(request.user, view.nick)
  actor_nicks = (contact_nicks +
                 admins +
                 members +
                 [view.nick] +
                 [s.owner for s in streams.values()] +
                 [e.actor for e in entries])
  actors = api.actor_get_actors(request.user, actor_nicks)

  # here comes lots of munging data into shape
  contacts = [actors[x] for x in contact_nicks if actors[x]]
  streams = display.prep_stream_dict(streams, actors)
  entries = display.prep_entry_list(entries, streams, actors)
  admins = [actors[x] for x in admins if actors[x]]
  members = [actors[x] for x in members if actors[x]]

  # END inbox generation chaos

  presence = api.presence_get(request.user, view.nick)

  # for sidebar_members
  members_count = view.extra['member_count']
  members_more = members_count > CONTACTS_PER_PAGE

  # for sidebar_admins
  admins_count = view.extra['admin_count']
  admins_more = admins_count > CONTACTS_PER_PAGE

  # for sidebar My Group POBoxes
  if(request.user):
    channels = api.actor_get_channels_member(request.user, request.user.nick,
                                limit=(CHANNELS_SIDEBAR + 1))
  else:
    channels = []

  channels_count = view.extra.get('channel_count', 0)
  channels_more = channels_count > CHANNELS_PER_PAGE

  childs = api.channel_get_related(request.user, view)

  # config for templates
  green_top = True
  sidebar_green_top = True
  selectable_icons = display.SELECTABLE_ICONS
  actor_link = True


  # for sidebar streams (copied from actor/views.py.  refactor)
  view_streams = dict([(x.key().name(), streams[x.key().name()])
                       for x in actor_streams])
  if request.user:
    # un/subscribe buttons are possible only, when logged in

    # TODO(termie): what if there are quite a lot of streams?
    for stream in view_streams.values():
      stream.subscribed = api.subscription_exists(
          request.user,
          stream.key().name(),
          'inbox/%s/overview' % request.user.nick
          )

  area = 'channel'
  tab = 'local'
  c = template.RequestContext(request, locals())

  if format == 'html':
    t = loader.get_template('channel/templates/history.html')
    return http.HttpResponse(t.render(c))
  elif format == 'json':
    t = loader.get_template('channel/templates/history.json')
    r = util.HttpJsonResponse(t.render(c), request)
    return r
  elif format == 'atom':
    t = loader.get_template('channel/templates/history.atom')
    r = util.HttpAtomResponse(t.render(c), request)
    return r
  elif format == 'rss':
    t = loader.get_template('channel/templates/history.rss')
    r = util.HttpRssResponse(t.render(c), request)
    return r

def channel_twitter(request, nick):
  _nick = nick
  nick = clean.channel(nick)

  view = api.channel_get_safe(request.user, nick)
  if not view:
    return http.HttpResponseRedirect('/hashtag/%s' % _nick)
  
  #twitter
  unauth = twitter.is_unauth(request)
  if 'twitter' in request.POST:
    status = twitter.post_update(request)

  handled = common_views.handle_view_action(
      request,
      {
       'channel_join': request.path,
       'channel_part': request.path,
       'channel_post': request.path,
       }
      )

  if handled:
    return handled

  page = util.paging_get_page(request)
  more = page+1

  try:
    entries = twitter.twitter_search(request, '#%s' % _nick, page)
    twitter_error = False
  except:
    entries = []
    twitter_error = True

  if not twitter_error:
    size_entries = len(entries)

  user_can_post, user_is_admin = _user_permissions(request, view)
  
  for entry in entries:
    entry['source'] =util.htmlentities_decode(entry.get('source'))

  # for sidebar_members
  members_count = view.extra['member_count']
  members_more = members_count > CONTACTS_PER_PAGE
  
  members = api.channel_get_members(request.user, channel=view.nick)
  actors = api.actor_get_actors(request.user, members)
  members = [actors[x] for x in members if actors[x]]

  if(request.user):
    channels = api.actor_get_channels_member(request.user, request.user.nick,
                              limit=(CHANNELS_SIDEBAR + 1))
  else:
    channels = []

  childs = api.channel_get_related(request.user, view)
  
  area = 'channel'
  tab = 'channel-twitter'

  green_top = True
  sidebar_green_top = True

  c = template.RequestContext(request, locals())
  t = loader.get_template('channel/templates/twitter.html')
  return http.HttpResponse(t.render(c))

def channel_item(request, nick, item=None, format='html'):
  nick = clean.channel(nick)
  logging.info('user: %s' % request.user)
  logging.info('nick: %s' % nick)
  view = api.actor_lookup_nick(request.user, nick)

  if not view:
    raise http.Http404()

  stream_ref = api.stream_get_presence(request.user, view.nick)

  entry = '%s/%s' % (stream_ref.key().name(), item)

  entry_ref = api.entry_get(request.user, entry)
  if not entry_ref:
    raise http.Http404()

  handled = common_views.handle_view_action(
      request,
      {'entry_add_comment': entry_ref.url(request=request), 
       'entry_remove': view.url(request=request),
       'entry_remove_comment': entry_ref.url(request=request),
       'entry_mark_as_spam': entry_ref.url(request=request)
       }
      )
  if handled:
    return handled

  admins = api.channel_get_admins(request.user, channel=view.nick)
  user_is_admin = request.user and request.user.nick in admins

  comments = api.entry_get_comments(request.user, entry)

  actor_nicks = [entry_ref.owner, entry_ref.actor] + [c.actor for c in comments]
  actors = api.actor_get_actors(request.user, actor_nicks)

  # Creates a copy of actors with lowercase keys (Django #6904: template filter
  # dictsort sorts case sensitive), excluding channels and the currently
  # logged in user.
  participants = {}
  for k, v in actors.iteritems():
    if (v and
        not v.is_channel() and
        not (hasattr(request.user, 'nick') and request.user.nick == v.nick)):
      participants[k.lower()] = v

  # display munge
  entry = display.prep_entry(entry_ref,
                             { stream_ref.key().name(): stream_ref },
                             actors)
  comments = display.prep_comment_list(comments, actors)

  # config for template
  green_top = True
  sidebar_green_top = True

  # rendering
  c = template.RequestContext(request, locals())
  if format == 'html':
    t = loader.get_template('channel/templates/item.html')
    return http.HttpResponse(t.render(c))
  elif format == 'json':
    t = loader.get_template('actor/templates/item.json')
    r = http.HttpResponse(t.render(c))
    r['Content-type'] = 'text/javascript'
    return r


def init_data(request, format='html'):

  tag_relations = api.init_data()

  area = 'tags'
  c = template.RequestContext(request, locals())

  # TODO(tyler): Other output formats.
  if format == 'html':
    t = loader.get_template('channel/templates/data.html')
    return http.HttpResponse(t.render(c))


def channel_browse(request, format='html', tagkey=None):
  per_page = CHANNELS_PER_PAGE
  page = util.paging_get_page(request)
  filter = util.paging_filter(request)
  type = util.paging_type(request)

  if request.user:
    view = request.user
    owner = api.actor_lookup_nick(view, util.get_owner(request))
  else:
    view = api.ROOT
    owner = api.actor_lookup_nick(view, view.nick)

  nick = view.nick

  if filter == 'member':
    actors, size = api.channel_browse_tagkey(view, per_page, page, tagkey, type, nick)
  else:
    actors, size = api.channel_browse_tagkey(view, per_page, page, tagkey, type)

  start, end, next, prev, first, last = util.paging(page, per_page, size)
  
  for c in actors:
    if request.user:
      c.i_am_member = api.actor_is_a_member(request.user, request.user.nick, c.nick)
    else:
      c.i_am_member = False
    c.tags_ref = api.channel_get_tags(view, c.tags)

  if tagkey is not None:
    base_url = '/channel/browse%s?' % tagkey
    breadcrumb = channel_helper.get_breadcrumb(view, tagkey)
  else:
    base_url = '/channel?'
    
  filter_url = util.paging_url(filter, nick, owner.nick)

  type_url = ''
  if type is not None:
    type_url = '&type=%s' % type

  countries = api.tags_get_countries(view, util.get_metadata('DEFAULT_TAG'))

  if request.user:
    country_tag = request.user.extra.get('country_tag', '/tag_geo/North America/United States')
  else:
    country_tag = '/tag_geo/North America/United States'

  channel_nicks, other = api.channel_browse_tagkey(view, 5, 1, country_tag)

  related_tags = api.channel_get_children_tags(view, tagkey)    
  related_tags = api.channel_get_tags(view, related_tags)

  show_tags_url = True
  
  channel_types = util.get_metadata('CHANNEL_TYPES')

  area = 'channel'
  
  c = template.RequestContext(request, locals())
  # TODO(tyler): Other output formats.
  if format == 'html':
    t = loader.get_template('channel/templates/browse_tag.html')
    return http.HttpResponse(t.render(c))

def channel_search(request, format='html'):
  q = request.GET.get('q', None)
  page   = util.paging_get_page(request)
  type = request.GET.get('type', None)

  if q is not None:
    actors, size = api.channel_search(request.user, q, page, CHANNELS_PER_PAGE, type)
  else:
    actors, size = [], 0


  for c in actors:
    c.i_am_member = api.actor_is_a_member(request.user, request.user.nick, c.nick)
    c.tags_ref = api.channel_get_tags(request.user, c.tags)
    
  start, end, next, prev, first, last = util.paging(page, CHANNELS_PER_PAGE, size)

  offset_text = 'More'
  area = 'channel'

  base_url = '/channel/search/?q=%s' % q
  
  type_url = ''
  if type is not None:
    type_url = '&type=%s' % type

  channels_member = api.actor_get_channels_member(request.user, request.user.nick,
                                                  limit=(CHANNELS_PER_PAGE + 1))

  c = template.RequestContext(request, locals())
  # TODO(tyler): Other output formats.
  if format == 'html':
    t = loader.get_template('channel/templates/search.html')
    return http.HttpResponse(t.render(c))


def get_pathtag(request, tag, format='json'):
  pathtag = api.get_pathtag(request.user, tag)  
  pathtag.reverse()
  area = 'channel'
  c = template.RequestContext(request, locals())
  if format == 'json':
    t = loader.get_template('channel/templates/pathtag.js')
    return http.HttpResponse(t.render(c))
  elif format == 'html':
    t = loader.get_template('channel/templates/pathtag.html')
    return http.HttpResponse(t.render(c))

def buildtree(tree):
  result = ""
  for t in tree:
    ch = ""
    if type(t) == list:
      childrens = buildtree(t[1])
      result += '{ attributes: {id: "node_%s"}, data: "%s", children: [%s]},' % (t[0].lower() , t[0], childrens)
    else:
      result += '{ attributes: {id: "node_%s"}, data: "%s", children: []},' % (t.lower(),t)
  return result

def buildtree_html(tree):
  result = ""
  for t in tree:
    ch = ""
    if type(t) == list:
      if len(t)> 1:
        childrens = buildtree_html(t[1])
        result += '<li> <a href="http://%s/channel/tag/%s/"> %s</a> <ul> %s </ul> </li> ' % (
            settings.DOMAIN, t[0],t[0], childrens)
      elif len(t):
        result += '<li> <a href="http://%s/channel/tag/%s/"> %s </a> </li>' % (settings.DOMAIN, t[0], t[0])
    else:
      result += '<li><a href="http://%s/channel/tag/%s/"> %s</a> </li>' % (settings.DOMAIN, t,t)
  return result


def channels_tags_all(request):
  logging.info('channels_tags_all')
  tag = request.REQUEST.get('tag', None)
  tags = api.channels_search_tags_all(request.user, tag)
    
  c = template.RequestContext(request, locals())
  t = loader.get_template('channel/templates/tags_all.json')
  r = util.HttpJsonResponse(t.render(c), request)
  return r
  
def channel_members(request, nick=None, format='html'):
  nick = clean.channel(nick)

  view = api.actor_lookup_nick(request.user, nick)

  if not view:
    raise exception.UserDoesNotExistError(nick, request.user)

  handled = common_views.handle_view_action(
      request,
      { 'actor_add_contact': request.path,
        'actor_remove_contact': request.path, })
  if handled:
    return handled

  per_page = CONTACTS_PER_PAGE
  offset, prev = util.page_offset_nick(request)

  follower_nicks = api.channel_get_members(request.user,
                                           view.nick,
                                           limit=(per_page + 1),
                                           offset=offset)
  actor_nicks = follower_nicks
  actors = api.actor_get_actors(request.user, actor_nicks)
  # clear deleted actors
  actors = dict([(k, v) for k, v in actors.iteritems() if v])
  per_page = per_page - (len(follower_nicks) - len(actors))

  whose = "%s's" % view.display_nick()

  # here comes lots of munging data into shape
  actor_tiles = [actors[x] for x in follower_nicks if x in actors]

  actor_tiles_count = view.extra.get('member_count', 0)
  actor_tiles, actor_tiles_more = util.page_actors(request,
                                                   actor_tiles,
                                                   per_page)

  area = 'channels'

  c = template.RequestContext(request, locals())

  if format == 'html':
    t = loader.get_template('channel/templates/members.html')
    return http.HttpResponse(t.render(c))


@decorator.login_required
def channel_settings(request, nick, page='index'):
  logging.info("channel_settings")
  nick = clean.channel(nick)

  view = api.actor_lookup_nick(request.user, nick)

  if not view:
    # Channel doesn't exist, bounce the user back so they can create it.
    # If the channel was just deleted, don't.  This unfortunately, misses the
    # case where a user is attempting to delete a channel that doesn't
    # exist.
    return http.HttpResponseRedirect('/channel/%s' % nick)

  if page == 'details':
    logging.info("channel_settings_details: %s" % nick)
    channel_types = api.get_config_values(api.ROOT, 'channel_type')
    if request.method == "POST":
      tags = request.POST.getlist('tags[]')
      view.tags = tags
      view.put()
      
  handled = common_views.handle_view_action(
      request,
      {
        'channel_update': request.path,
        'actor_remove' : '/channel',
      }
  )
  
  if page == 'photo' and not handled:
    handled = common_views.common_photo_upload(request, request.path, nick)
  if page == 'design' and not handled:
    handled = common_views.common_design_update(request, nick)
    
  if handled:
    return handled

  area = 'settings'
  avatars = display.DEFAULT_AVATARS
  actor_url = '/channel/%s' % nick

  if page == 'index':
    pass
  elif page == 'badge':
    badges = [{'id': 'badge-stream',
               'width': '200',
               'height': '300',
               'src': '/themes/%s/badge.swf' % settings.DEFAULT_THEME,
               'title': 'Stream',
               },
              {'id': 'badge-map',
               'width': '200',
               'height': '255',
               'src': '/themes/%s/badge-map.swf' % settings.DEFAULT_THEME,
               'title': 'Map',
               },
              {'id': 'badge-simple',
               'width': '200',
               'height': '200',
               'src': '/themes/%s/badge-simple.swf' % settings.DEFAULT_THEME,
               'title': 'Simple',
               },
              ]
  elif page == 'delete':
    pass
  elif page == 'design':
    pass
  elif page == 'details':
    pass
  elif page == 'photo':
    pass
  elif page == 'tags':
    pass
  else:
    return common_views.common_404(request)

  # full_page adds the title of the sub-component.  Not useful if it's the
  # main settings page
  if page != 'index':
    full_page = page.capitalize()

  # rendering
  c = template.RequestContext(request, locals())
  t = loader.get_template('channel/templates/settings_%s.html' % page)
  return http.HttpResponse(t.render(c))

def _user_permissions(request, view):
  if not request.user:
    return False, False
  elif api.channel_has_admin(request.user, view.nick, request.user.nick):
    return True, True
  elif api.channel_has_member(request.user, view.nick, request.user.nick):
    return True, False
  return False, False