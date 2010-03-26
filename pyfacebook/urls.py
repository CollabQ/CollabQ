from django.conf.urls.defaults import *

# You'd want to change this to wherever your app lives
urlpatterns = patterns('pyfacebook.views',
    # Some functionality - users can post text to their homepage
    (r'^canvas/post/', 'post'),

    # For the mock AJAX functionality
    (r'^canvas/ajax/', 'ajax'),

    # This is the canvas callback, i.e. what will be seen
    # when you visit http://apps.facebook.com/<appname>.
    (r'^canvas/', 'canvas'),

    # Extra callbacks can be set in the Facebook app settings
    # page. For example, post_add will be called when a user
    # has added the application.
    (r'^post_add/', 'post_add'),

)

handler404 = 'common.views.common_404'
handler500 = 'common.views.common_500'