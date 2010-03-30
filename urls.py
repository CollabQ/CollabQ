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

from django.conf import settings
from django.conf.urls.defaults import *

from common import patterns as common_patterns

urlpatterns = patterns('',
)

# FRONT
urlpatterns += patterns('front.views',
    (r'^$', 'front_front'),
)


# XMPP
urlpatterns += patterns('',
    (r'_ah/xmpp/message', 'api.views.api_vendor_xmpp_receive'),
)

# EXPLORE
urlpatterns += patterns('explore.views',
    (r'^explore/(?P<format>json|xml|atom|rss)$', 'explore_recent'),
    (r'^explore$', 'explore_recent'),
    (r'^feed/(?P<format>json|xml|atom|rss)$', 'explore_recent'),
)

# JOIN
urlpatterns += patterns('join.views',
    (r'^join$', 'join_join'),
    (r'^welcome$', 'join_welcome'),
    (r'^welcome/1$', 'join_welcome_photo'),
    #@begin zero code
    #(r'^welcome/2$', 'join_welcome_mobile'),
    #(r'^welcome/3$', 'join_welcome_contacts'),
    #(r'^welcome/2$', 'join_welcome_contacts'),
    #@end
    (r'^welcome/done$', 'join_welcome_done'),
)

# INVITE
urlpatterns += patterns('invite.views',
    (r'^invite/email/(?P<code>\w+)', 'invite_email'),
)

# CONFIRM
urlpatterns += patterns('confirm.views',
    (r'^confirm/email/(?P<code>\w+)$', 'confirm_email'),
)

# FLAT
urlpatterns += patterns('flat.views',
    (r'^tour$', 'flat_tour'),
    (r'^tour/1$', 'flat_tour', {'page': 'create'}),
    (r'^tour/2$', 'flat_tour', {'page': 'contacts'}),
    (r'^about$', 'flat_about'),
    (r'^privacy$', 'flat_privacy'),
    (r'^terms$', 'flat_terms'),
    (r'^terms$', 'flat_press'),
    (r'^help$', 'flat_help'),
    (r'^sms$', 'flat_help', {'page': 'sms'}),
    (r'^help/im$', 'flat_help', {'page': 'im'}),
    (r'^help/commands$', 'flat_help', {'page': 'commands'}),
)

##### ADMINISTRATION #####

# INSTALL
urlpatterns += patterns('administration.views',
  (r'^install$', 'install'),
)

# CHANNELS
urlpatterns += patterns('administration.views',
  (r'^admin/?$','admin'),
  (r'^admin/site$','admin_site'),
  (r'^admin/channels$','admin_channel'),
  (r'^admin/channels/list$','admin_channel_list'),
  (r'^admin/channels/new$','admin_channel_new'),
  (r'^admin/auto/(?P<action>[\w_\-\d]+)$','admin_auto'),
  url(r'^channel/(?P<nick>\w+)/enable$','admin_channel_enable', name='channel_enable'),
  url(r'^channel/(?P<nick>\w+)/disable$','admin_channel_disable', name='channel_disable'),
)

# CHANNEL
urlpatterns += patterns('channel.views',
    (r'^channel/tag/all$', 'channels_tags_all'),
    (r'^channel/browse(?P<tagkey>[\w\s\/\.\d]+)', 'channel_browse'),
    (r'^channel$', 'channel_browse'),
    (r'^channel/search/$', 'channel_search'),
    (r'^channel/create$', 'channel_create'),
    (r'^channel/(?P<nick>\w+)/presence/(?P<item>[\da-f]+)/(?P<format>json|xml|atom)$', 'channel_item'),
    (r'^channel/(?P<nick>\w+)/presence/(?P<item>[\da-f]+)$', 'channel_item'),
    (r'^channel/(?P<nick>\w+)/(?P<format>json|xml|atom|rss)$', 'channel_history'),
    (r'^channel/(?P<nick>\w+)$', 'channel_history', {'format': 'html'}),
    (r'^channel/(?P<nick>\w+)/members/(?P<format>json|xml|atom|rss)$', 'channel_members'),
    (r'^channel/(?P<nick>\w+)/members$', 'channel_members', {'format': 'html'}),
    (r'^channel/(?P<nick>\w+)/settings$', 'channel_settings'),
    (r'^channel/(?P<nick>\w+)/settings/(?P<page>\w+)$', 'channel_settings'),
    (r'^channel/(?P<nick>\w+)/twitter/?$', 'channel_twitter'),
    (r'^init$', 'init_data'),
)
urlpatterns += patterns('',
    (r'^c/(?P<the_rest>.*)$', 
     'django.views.generic.simple.redirect_to',
     {'url': '/channel/%(the_rest)s'}),           
)

# SETTINGS redirect
urlpatterns += patterns('actor.views',
    (r'^settings', 'actor_settings_redirect')
)


# LOGIN
urlpatterns += patterns('login.views',
    (r'^login$', 'login_login'),
    (r'^login/noreally$', 'login_noreally'),
    (r'^login/forgot$', 'login_forgot'),
    (r'^login/reset', 'login_reset'),
    (r'^logout$', 'login_logout'),
)

# API
urlpatterns += patterns('',
    (r'^api/', include('api.urls')),
    (r'^api', 'django.views.generic.simple.redirect_to', {'url': '/api/docs'}),
)


# BLOG
if settings.BLOG_ENABLED:
  urlpatterns += patterns('',
    (r'^blog/feed$', 
     'django.views.generic.simple.redirect_to', 
     {'url': settings.BLOG_FEED_URL}
    ),
    (r'^blog$', 
     'django.views.generic.simple.redirect_to', 
     {'url': settings.BLOG_URL}
    ),
  )

# BADGES
urlpatterns += patterns('',
    (r'^badge/(?P<format>image|js-small|js-medium|js-large|json|xml)/(?P<nick>\w+)$', 'badge.views.badge_badge'),
    (r'^user/(?P<nick>\w+)/feed/badge$', 'actor.views.actor_history', {'format': 'rss'}),
    (r'^channel/(?P<nick>\w+)/feed/badge$', 'channel.views.channel_history', {'format': 'rss'}),
)


# COMMON
urlpatterns += patterns('common.views',
    (r'^error$', 'common_error'),
    (r'^confirm$', 'common_confirm'),
    (r'^(?P<path>.*)/$', 'common_noslash'),
)

# BLOB
urlpatterns += patterns('blob.views',
    (common_patterns.AVATAR_PATH_RE, 'blob_image_jpg'),
)

#HAS TAG
urlpatterns += patterns('hashtag.views',
  (r'^hashtag$','hashtag_search'),
  (r'^hashtag/(?P<tag>[a-zA-Z][a-zA-Z0-9]*)$','hashtag_search'),
  (r'^hashtag/(?P<tag>[a-zA-Z][a-zA-Z0-9]*)/$','hashtag_search'),
)


##########################################################
# Twitter integration
##########################################################

# API

# Oauth
urlpatterns += patterns('',
  (r'^oauth/request_token', 'api.views.api_request_token'),
  (r'^oauth/access_token', 'api.views.api_access_token'),
  (r'^oauth/authorize', 'api.views.api_authorize'),
)

# Account
urlpatterns += patterns('',
  (r'^account/verify_credentials\.(?P<format>html|xml|json)', 'wrapper.views.verify_credentials'),
)

# Statuses
urlpatterns += patterns('',
  (r'^statuses/show/(?P<entry_id>[\w\d]+)\.(?P<format>html|xml|json)','wrapper.views.statuses_show')
)

##########################################
# Externals Services and OpenID
##########################################
urlpatterns += patterns('',
   (r'^openid/', include('openidgae.urls')),
   (r'^openid/', include('openidgae.urls')),
)

urlpatterns += patterns('',
   url(r'^openid/google','poboxopenid.views.openid_google'),
   url(r'^openid/login','poboxopenid.views.openid_login'),
   url(r'^openid/processuser','poboxopenid.views.openid_createuser'),
)

urlpatterns += patterns('',
   (r'^twitter/processuser','poboxopenid.views.twitter_user_create'),
   #(r'^facebook/signin$','poboxopenid.views.facebook_processuser'),
   #(r'^facebook/canvas$','poboxopenid.views.facebook_canvas'),
)
# OAuth twitter
urlpatterns += patterns('',
    (r'^twitter/auth$','actor.views.actor_twitter_auth' ),
    (r'^twitter/signin$','actor.views.actor_twitter_signin' ),
    (r'^twitter/callback$','actor.views.actor_twitter_callback' ),
    (r'^twitter/post_update$','actor.views.actor_post_update'),
    (r'^twitter/removing_token$','actor.views.actor_removing_token'),
)

##########################################################
# Actors
##########################################################
# ACTOR
urlpatterns += patterns('',
    (r'^user/search', 'actor.views.actor_search'),
    (r'^user/search/(?P<query>.*)', 'actor.views.actor_search'),
    (r'^user/email', 'actor.views.actor_email_update'),
    (r'^inbox$', 'actor.views.actor_direct_messages'),
    (r'^inbox/sent$', 'actor.views.actor_direct_messages', {'inbox':'sent'}),
    (r'^user/(?P<nick>\w+)', include('actor.urls')),
    (r'^user/(?P<nick>\w+)/', include('actor.urls')),
    (r'^search/user$', 'actor.views.actor_search'),
)

#ACTOR full name
urlpatterns += patterns('',
    (r'^(?P<nick>\w+)', include('actor.urls')),
    (r'^(?P<nick>\w+)/', include('actor.urls')),
)

#Server Errors
handler404 = 'common.views.common_404'
handler500 = 'common.views.common_500'