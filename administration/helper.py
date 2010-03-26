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