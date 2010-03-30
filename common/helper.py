# Copyright 2010 http://www.collabq.com
import logging
import time

from common import api
from common import util
from common import display

CONTACTS_PER_PAGE = 15
CHANNELS_PER_PAGE = 4

def get_inbox_entries(request, inbox, hide_comments=False, entries_per_page=20, filter=False, view=None):
  entries = api.entry_get_entries(request.user, inbox, hide_comments)
  if filter and view is not None:
    entries = api.filter_entries(request.user, entries, view.nick)
  per_page = entries_per_page - (len(inbox) - len(entries))
  return util.page_entries(request, entries, per_page)

def assemble_inbox_data(request, entries, actor_streams, inbox_owner_ref):
  stream_keys = [e.stream for e in entries]
  stream_keys += [s.key().name() for s in actor_streams]
  streams = api.stream_get_streams(request.user, stream_keys)

  contact_nicks = api.actor_get_contacts_safe(request.user,
                                              inbox_owner_ref.nick,
                                              limit=CONTACTS_PER_PAGE)
  channels = api.actor_get_channels_member_safe(request.user,
                                                     inbox_owner_ref.nick,
                                                     limit=CHANNELS_PER_PAGE)

  actor_nicks = (contact_nicks +
                 [inbox_owner_ref.nick] +
                 [s.owner for s in streams.values()] +
                 [e.owner for e in entries] +
                 [e.actor for e in entries])
  actors = api.actor_get_actors(request.user, actor_nicks)

  # here comes lots of munging data into shape
  contacts = [actors[x] for x in contact_nicks if actors[x]]
  streams = display.prep_stream_dict(streams, actors)
  entries = display.prep_entry_list(entries, streams, actors)

  return (contacts, channels, streams, entries)