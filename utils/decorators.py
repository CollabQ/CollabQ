import logging
from google.appengine.api import users

def required_admin(f):
  def wrapper(req):
    user = users.get_current_user()
    if not user:
      return http.HttpResponseRedirect(users.create_login_url('/install'))
    else:
      if not users.is_current_user_admin():
        return http.HttpResponseRedirect('/')
    return f(req)
  return wrapper

