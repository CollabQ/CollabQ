#!/usr/bin/python

import time

from openid.association import Association as xAssociation
from openid.store.interface import OpenIDStore
from openid.store import nonce

from google.appengine.ext import db

import models

class DatastoreStore(OpenIDStore):
  """An OpenIDStore implementation that uses the datastore. See
  openid/store/interface.py for in-depth descriptions of the methods.

  They follow the OpenID python library's style, not Google's style, since
  they override methods defined in the OpenIDStore class.
  """

  def storeAssociation(self, server_url, assoc):
    """
    This method puts a C{L{Association <openid.association.Association>}}
    object into storage, retrievable by server URL and handle.
    """
    assoc = models.Association(url=server_url,
                        handle=assoc.handle,
                        association=assoc.serialize())
    assoc.put()

  def getAssociation(self, server_url, handle=None):
    """
    This method returns an C{L{Association <openid.association.Association>}}
    object from storage that matches the server URL and, if specified, handle.
    It returns C{None} if no such association is found or if the matching
    association is expired.

    If no handle is specified, the store may return any association which
    matches the server URL. If multiple associations are valid, the
    recommended return value for this method is the one that will remain valid
    for the longest duration.
    """
    query = models.Association.all().filter('url', server_url)
    if handle:
      query.filter('handle', handle)

    results = query.fetch(1)
    if len(results) > 0:
      assoc = xAssociation.deserialize(results[0].association)
      if assoc.getExpiresIn() > 0:
        # hasn't expired yet
        return assoc

    return None

  def removeAssociation(self, server_url, handle):
    """
    This method removes the matching association if it's found, and returns
    whether the association was removed or not.
    """
    query = models.Association.gql('WHERE url = :1 AND handle = :2',
                            server_url, handle)
    return self._delete_first(query)

  def useNonce(self, server_url, timestamp, salt):
    if abs(timestamp - time.time()) > nonce.SKEW:
      return False
    
    anonce = str((str(server_url), int(timestamp), str(salt)))
    results = models.Nonce.gql("WHERE nonce = :1", anonce)
    if results.count() > 0:
      return False
    else:
      n = models.Nonce(nonce=anonce, timestamp=int(timestamp))
      n.put()
      return True

  def cleanunNonces(self):
    now = time.time()
    expired = []
    for n in models.Nonce.all():
      if abs(n.timestamp - now) > nonce.SKEW:
        expired.append(n)

    for n in expired:
      n.delete()

    return len(expired)


  def _delete_first(self, query):
    """Deletes the first result for the given query.

    Returns True if an entity was deleted, false if no entity could be deleted
    or if the query returned no results.
    """
    results = query.fetch(1)

    if results:
      try:
        results[0].delete()
        return True
      except db.Error:
        return False
    else:
      return False
