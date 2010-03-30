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

from common import util
from common import validate

def validate_and_save_string(name, value, min=1, max=100, message=""):
  validate.length(value, min, max, message)
  return util.set_metadata(name, value)

def validate_and_save_sitesettings(site_name, tagline, post_name, description=None):
  validate_and_save_string('SITE_NAME', site_name, message='Site Name')
  #validate_and_save_string('TAGLINE', tagline, message='Tagline')
  validate_and_save_string('POST_NAME', post_name, message='Post Name')
  if description is not None:
    validate_and_save_string('SITE_DESCRIPTION', description, message='Description')