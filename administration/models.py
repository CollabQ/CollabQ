import logging
from google.appengine.ext import db
from common import properties

class Metadata(db.Model):
  name = db.StringProperty(required=True)
  value = db.StringProperty(required=True)
  order = db.IntegerProperty(required=True, default=0)
  extra = properties.DictProperty()
  created_at = db.DateTimeProperty(auto_now_add=True)
  updated_at = db.DateTimeProperty(auto_now=True)

  def get_value(self):
    if 'type' in self.extra:
      if self.extra.get('type') == 'bool':
        if self.value == 'True':
          return True
        elif self.value == 'False':
          return False
        else:
          return None
    return self.value