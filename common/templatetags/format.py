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

import datetime
import logging
import re

from markdown import markdown2

from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.timesince import timesince
from common.util import create_nonce, safe, display_nick, url_nick

from common import clean
from common import models

register = template.Library()

link_regex = re.compile(r'\[([^\]]+)\]\((http[^\)]+)\)')

r'(^|\s|>)([A-Za-z][A-Za-z0-9+.-]{1,120}:[A-Za-z0-9/](([A-Za-z0-9$_.+!*,;/?:@&~=-])|%[A-Fa-f0-9]{2}){1,333}(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*,;/?:@&~=%-]{0,1000}))?)'

# lifted largely from: 
# http://www.manamplified.org/archives/2006/10/url-regex-pattern.html
autolink_regex = re.compile(r'(^|\s|>)([A-Za-z][A-Za-z0-9+.-]{1,120}:[A-Za-z0-9/](([A-Za-z0-9$_.+!*,;/?:@&~=-])|%[A-Fa-f0-9]{2}){1,333}(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*,;/?:@&~=%-]{0,1000}))?)')
bold_regex = re.compile(r'\*([^*]+)\*')
italic_regex = re.compile(r'_([^_]+)_')

core_plural_rules = [
          (r'(.*)(xpress)$',r'\1\2ions'), #custom
          (r'(.*)(s)tatus$',r'\1\2tatuses'),
          (r'(.*)(quiz)$',r'\1\2zes'),
          (r'^(ox)$',r'\1en'),
          (r'(.*)([m|l])ouse$',r'\1\2ice'),
          (r'(.*)(matr|vert|ind)(ix|ex)$',r'\1\2\3ices'),
          (r'(.*)(x|ch|ss|sh)$',r'\1\2es'),
          (r'(.*)([^aeiouy]|qu)y$',r'\1\2ies'),
          (r'(.*)(hive)$',r'\1\2s'),
          (r'(.*)(?:([^f])fe|([lr])f)$',r'\1\2\3ves'),
          (r'(.*)sis$',r'\1ses'),
          (r'(.*)([ti])um$',r'\1\2a'),
          (r'(.*)(p)erson$',r'\1\2eople'),
          (r'(.*)(m)an$',r'\1\2en'),
          (r'(.*)(c)hild$',r'\1\2hildren'),
          (r'(.*)(buffal|tomat)o$',r'\1\2oes'),
          (r'(.*)(alumn|bacill|cact|foc|fung|nucle|radi|stimul|syllab|termin|vir)us$',r'\1\2i'),
          (r'(.*)us$',r'\1uses'),
          (r'(.*)(alias)$',r'\1\2es'),
          (r'(.*)(ax|cris|test)is$',r'\1\2es'),
          (r'(.*)s$',r'\1s'),
          (r'^$',r''),
          (r'(.*)$',r'\1s'),
        ]

uninflected_plural = ['.*[nrlm]ese', 'buzz', 'chatter', '.*deer', '.*fish', '.*measles', '.*ois', '.*pox', '.*sheep', 'Amoyese',
			'bison', 'Borghese', 'bream', 'breeches', 'britches', 'buffalo', 'cantus', 'carp', 'chassis', 'clippers',
			'cod', 'coitus', 'Congoese', 'contretemps', 'corps', 'debris', 'diabetes', 'djinn', 'eland', 'elk',
			'equipment', 'Faroese', 'flounder', 'Foochowese', 'gallows', 'Genevese', 'Genoese', 'Gilbertese', 'graffiti',
			'headquarters', 'herpes', 'hijinks', 'Hottentotese', 'information', 'innings', 'jackanapes', 'Kiplingese',
			'Kongoese', 'Lucchese', 'mackerel', 'Maltese', 'media', 'mews', 'moose', 'mumps', 'Nankingese', 'news',
			'nexus', 'Niasese', 'Pekingese', 'People', 'Piedmontese', 'pincers', 'Pistoiese', 'pliers', 'Portuguese', 'proceedings',
			'rabies', 'rice', 'rhinoceros', 'salmon', 'Sarawakese', 'scissors', 'sea[- ]bass', 'series', 'Shavese', 'shears',
			'siemens', 'species', 'swine', 'testes', 'trousers', 'trout', 'tuna', 'Vermontese', 'Wenchowese',
			'whiting', 'wildebeest', 'Yengeese'];

irregular_plural = {
			'atlas':'atlases',
			'beef':'beefs',
			'brother':'brothers',
			'child':'children',
			'corpus':'corpuses',
			'cow':'cows',
			'ganglion':'ganglions',
			'genie':'genies',
			'genus':'genera',
			'graffito':'graffiti',
			'hoof':'hoofs',
			'loaf':'loaves',
			'man':'men',
			'money':'monies',
			'mongoose':'mongooses',
			'move':'moves',
			'mythos':'mythoi',
			'numen':'numina',
			'occiput':'occiputs',
			'octopus':'octopuses',
			'opus':'opuses',
			'ox':'oxen',
			'penis':'penises',
			'person':'people',
			'sex':'sexes',
			'soliloquy':'soliloquies',
			'testis':'testes',
			'trilby':'trilbys',
			'turf':'turfs',
			}

def get_uninflected(word):
  for rule in uninflected_plural:
    if re.match(rule, word):
      return word
  return None

@register.filter(name="plural")
@safe
def plural(word, arg=None):
  res = get_uninflected(word)
  if res is not None:
    return res
  for rule, replace in core_plural_rules:
    if re.match(rule, word, re.IGNORECASE):
	  return re.sub(rule, replace, word)
  return word

@register.filter(name="pobox_escape")
@safe
def pobox_escape(value, arg=None):
  value = escape(value)
  return value

@register.filter(name="format_shorter")
@safe
def format_shorter(value, arg=None):
  if arg is not None:
    size = int(arg)
  else:
    size = 16
  if len(value) > size+2:
    return value[:size]+'...'
  return value

@register.filter(name="urlexternalize")
@safe
def urlexternalize(value, arg):
  if not value.startswith('http'):
    return 'http://%s' % value
  return value

@register.filter(name='tag_name')
@safe
def tag_name(value, arg):
  res = u''
  regex = r'[\w\s/_]+/(?P<tagname>[\w\s\.\d]+)'
  results = re.search(regex, value)
  if results:
	res = results.groupdict()['tagname']
  return res

@register.filter(name="display_nick")
@safe
def display_nick(value, arg=None):
  return re.sub(r'@.+', '', value)

@register.filter(name="format_fancy")
@safe
def format_fancy(value, arg=None):
  value = italic_regex.sub(r'<i>\1</i>', value)
  value = bold_regex.sub(r'<b>\1</b>', value)
  return value


@register.filter(name="format_links")
@safe
def format_links(value, arg=None):
  value = link_regex.sub(r'<a href="\2" target=_new>\1</a>', value)
  return value

@register.filter(name="format_autolinks")
@safe
def format_autolinks(value, arg=None):
  value = autolink_regex.sub(r'\1<a href="\2" target="_new">\2</a>', value)
  return value

# TODO(tyler): Combine these with validate
user_regex = re.compile(
    r'@([a-zA-Z][a-zA-Z0-9]{%d,%d})' 
    % (clean.NICK_MIN_LENGTH - 1, clean.NICK_MAX_LENGTH - 1)
    )
channel_regex = re.compile(
    r'#([a-zA-Z][a-zA-Z0-9]{%d,%d})' 
    % (clean.NICK_MIN_LENGTH - 1, clean.NICK_MAX_LENGTH - 1)
    )

@register.filter(name="format_actor_links")
@safe
def format_actor_links(value, request=None):
  """Formats usernames / channels
  """
  value = re.sub(user_regex,
                 lambda match: '@<a href="%s" rel="user">%s</a>' % (
                   models.actor_url(match.group(1), 'user', request=request),
                   match.group(1)),
                 value)

  value = re.sub(channel_regex,
                 lambda match: '#<a href="%s" rel="channel">%s</a>' % (
                   models.actor_url(match.group(1), 'channel', request=request),
                   match.group(1)),
                 value)
  return value

@register.filter(name="format_markdown")
@safe
def format_markdown(value, arg=None):
  return markdown2.markdown(value)

@register.filter(name="format_comment")
@safe
def format_comment(value, request=None):
  content = escape(value.extra.get('content', 'no title'))
  content = format_markdown(content)
  content = format_autolinks(content)
  content = format_actor_links(content, request)
  return content

@register.filter(name="truncate")
def truncate(value, arg):
  """
  Truncates a string after a certain number of characters. Adds an
  ellipsis if truncation occurs.
  
  Due to the added ellipsis, truncating to 10 characters results in an
  11 character string unless the original string is <= 10 characters
  or ends with whitespace.

  Argument: Number of characters to truncate after.
  """
  try:
    max_len = int(arg)
  except:
    return value # No truncation/fail silently.

  if len(value) > max_len:
    # Truncate, strip rightmost whitespace, and add ellipsis
    return value[:max_len].rstrip() + u"\u2026"
  else:
    return value

@register.filter(name="entry_icon")
@safe
def entry_icon(value, arg=None):
  icon = value.extra.get('icon', None)
  if not icon:
    return ""

  return '<img src="/themes/%s/icons/%s.gif" alt="%s" class="icon" />' % (settings.DEFAULT_THEME, icon, icon)

@register.filter(name="linked_entry_title")
@safe
def linked_entry_title(value, request=None):
  """
  Returns an entry link.

  value     an entry object.
  request   a HttpRequest (optional).
  """
  return '<a href="%s">%s</a>' % (
      value.url(request=request), 
      format_fancy(escape(value.extra['title'])).replace('\n', ' '))

@register.filter
@safe
def linked_entry_truncated_title(value, arg):
  """
  Returns a link to an entry using a truncated entry title as source anchor.

  Argument: Number of characters to truncate after.
  """
  try:
    max_len = int(arg)
  except:
    max_len = None # No truncation/fail silently.

  if value.is_comment():
    title = escape(truncate(value.extra['entry_title'].replace('\n', ' '),
                            max_len))
  else:
    title = escape(truncate(value.extra['title'].replace('\n', ' '), max_len))

  return '<a href="%s">%s</a>' % (value.url(), title)

@register.filter(name="stream_icon")
@safe
def stream_icon(value, arg=None):
  return '<img src="/themes/%s/icons/favku.gif" class="icon" />' % settings.DEFAULT_THEME
  if type(value) is type(1):
    return '<!-- TODO entry icon goes here -->'
  return '<!-- TODO entry icon goes here -->'

@register.filter(name="je_timesince")
@safe
def je_timesince(value, arg=None):
  d = value
  if (datetime.datetime.now() - d) < datetime.timedelta(0,60,0):
    return "a moment"
  else:
    return timesince(d)

@register.filter(name="utc_timesince")
@safe
def utc_timesince(value, arg=None):
  try:
    d = datetime.datetime.strptime(value, '%a %b %d %H:%M:%S +0000 %Y')
  except:
    d = datetime.datetime.strptime(value, '%a, %d %b %Y %H:%M:%S +0000')
  if (datetime.datetime.now() - d) < datetime.timedelta(0,60,0):
    return "a moment"
  else:
    return timesince(d)

@register.filter(name="sum")
@safe
def sum(value, arg=0):
  value = int(value)
  arg = int(arg)
  return value+arg

@register.filter
@safe
def entry_actor_link(value, request=None):
  """
  Returns an actor html link.

  value     an entry_actor object.
  request   a HttpRequest (optional).
  """
  return '<a href="%s">%s</a>' % (models.actor_url(url_nick(value),
                                                   'user',
                                                   request=request),
                                  display_nick(value))

class URLForNode(template.Node):
  def __init__(self, entity, request):
    self.entity = template.Variable(entity)
    self.request = template.Variable(request)

  def render(self, context):
    try:
      actual_entity = self.entity.resolve(context)
      actual_request = self.request.resolve(context)

      try:
        return actual_entity.url(request=actual_request)
      except AttributeError:
        # treat actual_entity as a string
        try:
          mobile = actual_request.mobile
        except AttributeError:
          mobile = False

        if mobile and settings.SUBDOMAINS_ENABLED:
          return 'http://m.' + settings.HOSTED_DOMAIN
        else:
          return 'http://' + str(actual_entity)

    except template.VariableDoesNotExist:
      return ''

@register.tag
def url_for_reply(parser, token):
  try:
    tag_name, entry, request = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError, \
      "%r tag requires exactly two arguments" % token.contents.split()[0]
  return ReplyCommentLinkNode(entry, request)

class ReplyCommentLinkNode(template.Node):
  def __init__(self, entry, request):
    self.entry = template.Variable(entry)
    self.request = template.Variable(request)

  def render(self, context):
    return self.request

@register.tag
def url_for(parser, token):
  """
  Custom tag for more easily being able to pass an HttpRequest object to
  underlying url() functions.
  
  One use case is being able to return mobile links for mobile users and
  regular links for others. This depends on request.mobile being set or
  not.

  Observe that if entity is not an object with the method url(), it is
  assumed to be a string.

  Parameters: entity, request.
  """
  try:
    tag_name, entity, request = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError, \
      "%r tag requires exactly two arguments" % token.contents.split()[0]
  return URLForNode(entity, request)

class ActorLinkNode(template.Node):
  def __init__(self, actor, request):
    self.actor = template.Variable(actor)
    self.request = template.Variable(request)

  def render(self, context):
    try:
      actual_actor = self.actor.resolve(context)
      actual_request = self.request.resolve(context)

      try:
        url = actual_actor.url(request=actual_request)
        full_name = actual_actor.extra.get('given_name', '') + " " + actual_actor.extra.get('family_name', '')
        return '<a href="%s" title="%s">%s</a>' % (url, full_name, actual_actor.display_nick())
      except AttributeError:
        return ''
    except template.VariableDoesNotExist:
      return ''

@register.tag
def actor_link(parser, token):
  """
  Custom tag for more easily being able to pass an HttpRequest object to
  underlying url() functions.
  
  One use case is being able to return mobile links for mobile users and
  regular links for others. This depends on request.mobile being set or
  not.

  Parameters: actor, request.
  """
  try:
    tag_name, actor, request = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError, \
      "%r tag requires exactly two arguments" % token.contents.split()[0]
  return ActorLinkNode(actor, request)

@register.tag
def showif(parser, token):
  bits = list(token.split_contents())
  if len(bits) != 3:
    raise template.TemplateSyntaxError, "%r takes two arguments" % bits[0]
  nodelist = parser.parse(('end'+bits[0], ))
  parser.delete_first_token()

  var1 = parser.compile_filter(bits[1])
  var2 = parser.compile_filter(bits[2])
  
  return ShowIfNode(var1, var2, nodelist)

@register.tag
def getvalue(parser, token):
  logging.info("tag getvalue")
  try:
    tag_name, key, list = token.split_contents()
  except ValueError:
    raise template.TemplateSyntaxError, \
      "%r tag requires exactly two arguments" % token.contents.split()[0]
  return GetValueNode(key, list)

class GetValueNode(template.Node):
  def __init__(self, key, list):
    self.key = template.Variable(key)
    self.list = template.Variable(list)
  def render(self, context):
    key = self.key.resolve(context)
    list = self.list.resolve(context)

    for k, value in list:
      if key == k:
        return value
      
    return 'Not found'

class ShowIfNode(template.Node):
  def __init__(self, key, list, nodelist):
    self.key = key
    self.list = list
    self.nodelist = nodelist
    
  def render(self, context):
    key = self.key.resolve(context)
    list = self.list.resolve(context)

    res = ''
    if key in list:
      res = self.nodelist.render(context)

    return res