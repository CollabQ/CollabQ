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