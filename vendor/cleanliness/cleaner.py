import datetime as datetime_mod
import re
import time as time_mod
import urlparse

# local imports
from cleanliness import exception
from cleanliness import encoding

# Cleaners
EMPTY_VALUES = (None, '')

def string_length(value, 
                  message="Must be between %(max)s and %(min)s characters", 
                  max_length=None, min_length=None):
  value = encoding.smart_unicode(value)
  value_length = len(value)
  message % {'max': max_length, 'min': min_length, 'length': value_length}
  if max_length is not None and value_length > max_length:
    raise exception.ValidationError(message)
  if min_length is not None and value_length < min_length:
    raise exception.ValidationError(message)
  return value

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

def date(value, message='Invalid date', 
         input_formats=DEFAULT_DATE_INPUT_FORMATS):
  if value in EMPTY_VALUES:
    return None
  if isinstance(value, datetime_mod.datetime):
    return value.date()
  if isinstance(value, datetime_mod.date):
    return value
  for format in input_formats:
    try:
      return datetime_mod.date(*time_mod.strptime(value, format)[:3])
    except ValueError:
      continue
  raise exception.ValidationError(message)

DEFAULT_DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)

def datetime(value, message='Invalid date',
             input_formats=DEFAULT_DATETIME_INPUT_FORMATS):
  if value in EMPTY_VALUES:
    return None
  if isinstance(value, datetime_mod.datetime):
    return value
  if isinstance(value, datetime_mod.date):
    return datetime_mod.datetime(value.year, value.month, value.day)
  if isinstance(value, list):
    # Input comes from a SplitDateTimeWidget, for example. So, it's two
    # components: date and time.
    if len(value) != 2:
      raise exception.ValidationError(message)
    value = '%s %s' % tuple(value)
  for format in input_formats:
    try:
      return datetime_mod.datetime(*time_mod.strptime(value, format)[:6])
    except ValueError:
      continue
  raise exception.ValidationError(message)

email_re = re.compile(
  r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
  r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
  r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain
def email(value, message='Invalid email address', 
          max_length=None, min_length=None):
  value = regex(value,
                regex_=email_re,
                message=message, 
                max_length=max_length, 
                min_length=min_length)
  return value

def regex(value, message, regex_, max_length=None, min_length=None):
  value = string_length(value, max_length=max_length, min_length=min_length)
  if not regex_.search(value):
    raise exception.ValidationError(message)
  return value

url_re = re.compile(
  r'^https?://' # http:// or https://
  r'(?:(?:[A-Z0-9-]+\.)+[A-Z]{2,6}|' #domain...
  r'localhost|' #localhost...
  r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
  r'(?::\d+)?' # optional port
  r'(?:/?|/\S+)$', re.IGNORECASE)

def url(value, message, max_length=None, min_length=None):
  # If no URL scheme given, assume http://
  if value and '://' not in value:
    value = u'http://%s' % value
  # If no URL path given, assume /
  if value and not urlparse.urlsplit(value)[2]:
    value += '/'
  value = string_length(value, max_length=max_length, min_length=min_length)
  return value

DEFAULT_TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)

def time(value, message='Invalid time',
         input_formats=DEFAULT_TIME_INPUT_FORMATS):
  if value in EMPTY_VALUES:
    return None
  if isinstance(value, datetime_mod.time):
    return value
  for format in input_formats:
    try:
      return datetime_mod.time(*time_mod.strptime(value, format)[3:6])
    except ValueError:
      continue
  raise exception.ValidationError(message)
