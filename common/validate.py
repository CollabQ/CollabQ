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

from re import match
import re
import logging

from common import exception
from common.models import Relation
from django import http
from common import patterns
from common import util

from django.conf import settings

# TODO(teemu): list of banned names should probably reside outside of code.
# Ask Andy, where to move this.
banned_names = [
    'address',
    'admin',
    'action',
    'blog',
    'city',
    'cities',
    'country',
    'countries',
    'create',
    'entry',
    'entries',
    'event',
    'events',
    'get',
    'group',
    'groups',
    'guide',
    'guides',
    'id',
    'hotspot',
    'json',
    'xmlrpc',
    'atom',
    'list',
    'location',
    'manage',
    'network',
    'person',
    'persons',
    'place',
    'places',
    'slug',
    'spot',
    'subscribe',
    'tag',
    'tags',
    'town',
    'towns',
    'user',
    'users',
    'support',
    'atom',
    'feed',
    'rss',
    'www',
    'xml',
    'bar',
    'cafe',
    'fashion',
    'hotel',
    'restaurant',
    'product',
    'review',
    'shop',
    'shopping',
    'static',
    'static1',
    'static2',
    'static3',
    'static4',
    'static5',
    'static6',
    'static7',
    'static8',
    'static9',
    'static10',
    'static11',
    'static12',
    'static13',
    'static14',
    'static15',
    'static16',
    'static17',
    'static18',
    'static19',
    'travel',
    'trip'
]

def avatar_path(path):
  # TODO(tyler): Move this to clean
  if not patterns.AVATAR_PARTIAL_PATH_COMPILED.match(path):
    raise exception.ValidationError('Could not validate avatar path')

def nonce(request, action=''):
  user = request.user

  expected_now = util.create_nonce(user, action)
  expected_older = util.create_nonce(user, action, offset=-1)

  # TODO(termie): we should probably only accept these in POST in the future
  given = request.REQUEST.get('_nonce') 
  if given not in (expected_now, expected_older):
    raise exception.ValidationError('Could not validate nonce')

def error_nonce(request, message=''):
  expected_now = util.create_nonce(None, message)
  expected_older = util.create_nonce(None, message, offset=-1)

  given = request.REQUEST.get('_error') 
  if given not in (expected_now, expected_older):
    raise exception.ValidationError('Could not validate nonce')


# Mobile number regexps 
_italian = re.compile(r"\+39.*")
_international= re.compile(r"\+.*")
_numeric = re.compile(r"\+\d*$")

def mobile_number(mobile):
  # The standard mobile number validation method django.core.validators.isValidPhone
  # is not suitable for us, as it expects only US numbers in hyphen-format.
  field = "mobile"
  if len(mobile) < 9:
    raise exception.ValidationError("Your mobile phone should be at least 9 digits long including the '+'", field)
  if not _international.match(mobile):
    raise exception.ValidationError("Your mobile number must be in the international format with a '+' in front of it.", field)
  if not _numeric.match(mobile):
    raise exception.ValidationError("Your mobile number can only be numbers besides the '+'", field)
  if _italian.match(mobile):
    raise exception.ValidationError("Sorry, Italian numbers are currently blocked due to abuse.", field)

def mobile_number_not_activated(mobile):
  pass

# TODO(mikie): check what we actually want to do to validate emails, this errs
# on the side of permissiveness
_email = re.compile(r"[^@]+@[^@]+\.[^@]+")
def email(email):
  if len(email) < 3 or not _email.match(email):
    raise exception.ValidationError("You have supply a valid email address")
  pass

def email_not_activated(email):
  pass

def sms_message(message):
  pass

def full_name(name): 
  length(name, 1, 2*60+1, "Your name", 'full_name')

_tagcountry = re.compile(r"[\w\s/_]+")
def country(country_tag):
  if not _tagcountry.match(country_tag):
    raise exception.ValidationError("Please, select your country")

def account_type(type):
  if not type in _get_config_values('account_type'):
    raise exception.ValidationError("Invalid value in Type")

def confirm_dangerous(request, message=None):
  # TODO(termie): change the javascript to submit POST messages
  #               and make this only check request.POST
  if "confirm" not in request.REQUEST:
    raise exception.ConfirmationRequiredException(message)

def name(s, message="Your name", field='name'):
  length(s, 1, 60, message, field)

def not_banned_name(s, message=None):
  if util.display_nick(s) in banned_names:
    raise exception.ValidationError("Screen name %s is not allowed." % s, "nick")

def privacy(s, message=None): pass

def password(s, message="Your password"):
  length(s, 6, 16, message, 'password')

def bool_checkbox(s, message="Invalid value in checkbox"):
  if not s in ['True', 'False', 'true', 'false', '1', '0', True, False]:
        raise exception.ValidationError(message)

def password_and_confirm(password, confirm, message="Your password",
                         field=None):
  if password != confirm:
    raise exception.ValidationError('The passwords do not match', field)
  length_password(password, 6, 16, message, 'password')

def length(s, min, max, message=None, field=None):
  if len(s) < min or len(s) > max:
    raise exception.ValidationError(
        (message or '') + " must be between %s and %s characters long" % (
            min, max),
        field)
  pass

def length_password(s, min, max, message=None, field=None):
  if len(s) < min or len(s) > max:
    raise exception.ValidationError(
        (message or '') + " must be between %s and %s characters long" % (
            min, max),
        field)
  pass

def avatar_photo_size(file):
  # file.size is in bytes
  if file.size > (settings.MAX_AVATAR_PHOTO_KB << 10):
    raise exception.ValidationError(
        "Avatar photo size must be under %s kilobytes"
        % (settings.MAX_AVATAR_PHOTO_KB,))
  pass

def location(s, message=None):
  pass

def uuid(s, message=None):
  pass

def stream(s, message=None):
  pass

def entry(s, message=None):
  pass

def user_nick(s, message=None):
  pass

def presence_extra(d, message=None):
  allowed_keys = set(['status', 'availability', 'location',
                      'senders_timestamp', 'activity',
                      'profile', 'presenceline', 'presenceline',
                      'bt', 'calendar', 'generated',
                      's60_settings'])
  if len(allowed_keys.union(set(d.keys()))) != len(allowed_keys):
    raise exception.ValidationError('illegal keys in presence')


def description(s, message=None):
  pass

def external_url(s, message=None):
  pass

_url = re.compile(
 	    r'^https?://' # http:// or https://
 	    r'(?:(?:[A-Z0-9]+(?:-*[A-Z0-9]+)*\.)+[A-Z]{2,6}|' #domain...
 	    r'localhost|' #localhost...
 	    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
 	    r'(?::\d+)?' # optional port
 	    r'(?:/?|/\S+)$', re.IGNORECASE)
def url(url, message=None):
  if len(url) < 10 or not _url.match(url):
    raise exception.ValidationError("You must supply a valid URL")
  pass

_format = re.compile(r'html|xhtml|json|xml|atom|rss')
def format_page(format, message=None):
  if not _format.match(format):
    raise http.Http404()

_channel_type = re.compile(r'leader|region|institution')
def channel_type(format, message="Invalid Channel Type"):
  if not _channel_type.match(format):
    raise exception.ValidationError(message)

def _get_config_values(owner):
  query = Relation.gql('WHERE relation = :1 and owner = :2',
                       'config_values',
                        owner)
  return [value.target for value in query.fetch(100)]