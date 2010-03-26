# vim:ts=2:sw=2:expandtab
import hashlib

from google.appengine.ext import db

class Association(db.Model):
  """An association with another OpenID server, either a consumer or a provider.
  """
  url = db.LinkProperty()
  handle = db.StringProperty()
  association = db.TextProperty()

class Nonce(db.Model):
  """An OpenID nonce.
  """
  nonce = db.StringProperty()
  timestamp = db.IntegerProperty()

class Person(db.Expando):
  """
  # Make sure that ax_dict/sreg_dict return the dict by reference, and
  # that changes get saved on put()
  >>> import models
  >>> p = models.Person()
  >>> p.ax_dict()
  {}
  >>> p.ax_dict()['horsie'] = 'doggie'
  >>> p.ax_dict()
  {'horsie': 'doggie'}
  >>> p.put() is not None
  True
  >>> import pickle
  >>> pickle.loads(p.ax)
  {'horsie': 'doggie'}

  # Ensure that pickle.dumps is not getting called on put() if we
  # haven't touched ax/sreg
  >>> p = models.Person()
  >>> hasattr(p, 'cache_ax')
  False
  >>> p.put() is not None
  True
  >>> hasattr(p, 'cache_ax')
  False
  """
  openid = db.StringProperty()
  date = db.DateTimeProperty(auto_now_add=True)
  # Pickled Simple Registration Response - Do not set directly, use
  # sreg_dict instead
  sreg = db.BlobProperty()
  # Pickled Attribute Exchange Response - Do not set directly, use
  # ax_dict instead
  ax = db.BlobProperty()

  def put(self):
    for name in ('sreg', 'ax'):
      if hasattr(self, '_cache_%s' % name):
        value = getattr(self, '_cache_%s' % name)
        import pickle
        setattr(self, name, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
    return super(Person, self).put()

  def get_depickled_version(self, propertyname):
    cachepropertyname = '_cache_%s' % propertyname
    if not hasattr(self, cachepropertyname):
      value = {}
      pickledvalue = getattr(self, propertyname, None)
      if pickledvalue:
        import pickle
        value = pickle.loads(pickledvalue)
      setattr(self, cachepropertyname, value)
    return getattr(self, cachepropertyname)

  def sreg_dict(self):
    return self.get_depickled_version('sreg')

  def ax_dict(self):
    return self.get_depickled_version('ax')

  def get_email(self):
    """Attemps to return the SReg or AX email address for this
    Person"""
    toreturn = self.sreg_dict().get('email', None)
    toreturn = self.ax_dict().get('email', toreturn)
    if isinstance(toreturn, list):
      if len(toreturn) > 0:
        toreturn = toreturn[0]
      else:
        toreturn = None
    return toreturn

  def get_field_value(self, field, default=None):
    toreturn = self.sreg_dict().get(field, None)
    toreturn = self.ax_dict().get(field, toreturn)
    if isinstance(toreturn, list):
      if len(toreturn) > 0:
        toreturn = toreturn[0]
      else:
        toreturn = default
    return toreturn

  def openidURI(self):
    from openid.yadis import xri
    if xri.identifierScheme(self.openid) == "XRI":
      return "http://xri.net/%s" % self.openid
    return self.openid

  def pretty_openid(self):
    return self.openid.replace('http://','').replace('https://','').rstrip('/').split('#')[0]

  def person_name(self):
    ax_dict = self.ax_dict()
    sreg_dict = self.sreg_dict()
    if ax_dict.get('firstname', False) and \
        ax_dict.get('lastname', False):
      firstname = ax_dict['firstname']
      if isinstance(firstname, list):
        firstname = firstname[0]
      lastname = ax_dict['lastname']
      if isinstance(lastname, list):
        lastname = lastname[0]
      return "%s %s" % (firstname, lastname)
    elif sreg_dict.get('fullname', False):
      return sreg_dict['fullname']
    else:
      return self.pretty_openid()

class Session(db.Expando):
  # the logged in person
  person = db.ReferenceProperty(Person)

  # OpenID library session stuff
  openid_stuff = db.TextProperty()

  def __init__(self, parent=None, key_name=None, **kw):
    """if key_name is None, generate a random key_name so that
       session_id cookies are not guessable
    """
    if 'key' in kw:
      key_name = kw.get('key').name()
    else:
      if key_name is None:
        import uuid
        key_name = uuid.uuid4()
        import binascii
        key_name = binascii.unhexlify(key_name.hex)
        import base64
        key_name = "S" + base64.urlsafe_b64encode(key_name).rstrip('=')
    super(db.Expando, self).__init__(parent=parent, key_name=key_name, **kw)
