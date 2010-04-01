# Copyright 2009 Google Inc.
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


# This is an example local_settings.py that will get the server to
# play nice with the local development server. You'll want to rename it
# local_settings.py before running ./bin/testserver.sh
DEBUG = False
TEMPLATE_DEBUG = False

COOKIE_DOMAIN = 'localhost'
NS_DOMAIN = 'example.com'
GAE_DOMAIN = 'example.com'
DOMAIN = 'localhost:8080'

ADMINS_POBOX= []

WILDCARD_USER_SUBDOMAINS_ENABLED = False
SUBDOMAINS_ENABLED = False
SSL_LOGIN_ENABLED = False

