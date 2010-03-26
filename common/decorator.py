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
from django.conf import settings

from common import exception
from common import util

def debug_only(handler):
  def _wrapper(request, *args, **kw):
    if not settings.DEBUG:
      raise http.Http404()
    return handler(request, *args, **kw)
  _wrapper.__name__ = handler.__name__
  return _wrapper

def authentication_required(handler):
  def _wrapper(request, *args, **kw):
    from common import user
    if (('oauth_token' in request.REQUEST and 'oauth_consumer_key' in request.REQUEST)
      or 'HTTP_AUTHORIZATION' in request.META):
      try:
        if not request.user:
          raise exception.AuthenticationException
      except:
        raise exception.AuthenticationException

    return handler(request, *args, **kw)
  _wrapper.__name__ = handler.__name__
  return _wrapper

def login_required(handler):
  def _wrapper(request, *args, **kw):
    if not request.user:
        raise exception.LoginRequiredException()
    return handler(request, *args, **kw)
  _wrapper.__name__ = handler.__name__
  return _wrapper

#@begin malaniz code
from google.appengine.api import users
import settings
import logging
def admin_required(handler):
  def _wrapper(request, *args, **kw):
    if not request.user:
      raise exception.LoginRequiredException()
    elif not request.user.nick in settings.ADMINS_POBOX:
      raise exception.AdminRequiredError
    return handler(request, *args, **kw)
  _wrapper.__name__ = handler.__name__
  return _wrapper
#@end malaniz code

def add_caching_headers(headers):
  def _cache(handler):
    def _wrap(request, *args, **kw):
      rv = handler(request, *args, **kw)
      return util.add_caching_headers(rv, headers)
    _wrap.func_name == handler.func_name
    return _wrap
  return _cache

# TOOD(termie): add caching headers to cache response forever
cache_forever = add_caching_headers(util.CACHE_FOREVER_HEADERS)

# TOOD(termie): add caching headers to cache response never
cache_never = add_caching_headers(util.CACHE_NEVER_HEADERS)

def gae_admin_required(function):
  def _wrap(request, *args, **kw):
    q = request.META['PATH_INFO']
    full_path = request.get_full_path()
    user = users.get_current_user()
    if not user:
      return http.HttpResponseRedirect(users.create_login_url(full_path))
    else:
      if not users.is_current_user_admin():
        raise exception.AdminRequiredError

    return function(request, *args, **kw)
  return _wrap