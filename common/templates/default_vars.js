//MAX_POST_LENGTH
{% if MAX_POST_LENGTH %}
  MAX_POST_LENGTH = {{MAX_POST_LENGTH}}
{% else %}
  MAX_POST_LENGTH = 140
{% endif %}

//MAX_TWITTER_LENGTH
{% if MAX_TWITTER_LENGTH %}
  MAX_TWITTER_LENGTH = {{MAX_TWITTER_LENGTH}}
{% else %}
  MAX_TWITTER_LENGTH = 140
{% endif %}

//DEBUG
{% if DEBUG %}
  DEBUG = true
{% else %}
  DEBUG = false
{% endif %}

//USER
{% if request.user %}
  NICK = "{{request.user.display_nick}}"
{% endif %}