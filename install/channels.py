import logging

from common import api
from common import memcache

channels = {}
#channels.append(['Channel_Name', ['tag1', 'tag2'], 'Description', 'Type'])

#Engineering
_channels = []
_channels.append(['Civil', ['Civil'], 'Channel Civil', 'Group'])
_channels.append(['Electrical', ['Electrical'], 'Channel Electrical', 'Group'])
_channels.append(['Electronics', ['Electronics'], 'Channel Electronics', 'Group'])
_channels.append(['ElectricalElectronics', ['Electrical','Electronics'], 'Channel ElectricalElectronics', 'Group'])
_channels.append(['Mechnical', ['Mechanical'], 'Channel Mechnical', 'Group'])
_channels.append(['Architecture', ['Architecture'], 'Channel Architecture', 'Group'])
_channels.append(['Computers', ['Computers'], 'Channel Computers', 'Group'])
_channels.append(['Instrumentation', ['Instrumentation'], 'Channel Instrumentation', 'Group'])
_channels.append(['Production', ['Production'], 'Channel Production', 'Group'])
_channels.append(['Metallurgy', ['Metallurgy'], 'Channel Metallurgy', 'Group'])
channels['Management Education'] = {'path':'Management Education', 'channels':_channels}

#============================================
#Management
_channels = []
_channels.append(['Marketing', ['Marketing'], 'Channel Marketing', 'Group'])
_channels.append(['Finance', ['Fiance'], 'Channel Finance', 'Group'])
_channels.append(['HR', ['HR'], 'Channel HR', 'Group'])
_channels.append(['TechnologyOperations', ['TechOps'], 'Channel TechnologyOperations', 'Group'])
_channels.append(['International', ['International'], 'Channel International', 'Group'])
_channels.append(['BusinessGovernment', ['BusinessGov'], 'Channel BusinessGovernment', 'Group'])
_channels.append(['Strategy', ['Strategy'], 'Channel Strategy', 'Group'])
channels['Engineering Education'] = {'path':'Engineering Education', 'channels':_channels}

tags = {}
#===============================================
# Root
#_tags = ['Information Technology', 'Leadership', 'Enterpreneurship', 'Communications', 'Social Media', 'Retail', 'Energy', 'Telecom',
#         'Real Estate', 'Games', 'Apparel', 'Automobile', 'Financial', 'Chemical', 'Entertainment', 'Education', 'Marketing', 'Law', 'Management Consulting']

_tags = ['Professional', 'Academic', 'Social']

#_tags = _tags + ['Business Management', 'Financial Accounting',
#                 'Office Administration',  'Media Art Design',  'Social Media',
#                 'Bio Tech',  'Customer Service',  'Human Resource',
#                 'Mobile App',  'Web 2.0 App',  'Web Design',  'Legal Paralegal',
#                 'Manufacturing',  'Automobile',  'Marketing',  'Advertising',
#                 'Biz Dev Sales',
#                 'Writing Editing',
#                 'Retail Wholesale',
#                 'Film TV Video',
#                 'Non Profit']

tags['Root'] = {'tags':_tags}

#===============================================
# Information Technology
#_tags = ['Programming', 'Databases', 'ERP',  'Web Dev',  'Mobile Apps',  'Business Intelligence',  'CRM',  'Operating Systems']
#tags['Information Technology'] = {'path':'Information Technology', 'tags':_tags}

_tags = ['Management Education', 'Engineering Education']
tags['Academic'] = {'path':'Academic', 'tags':_tags}

_tags = ['Web Dev', 'Mobile Apps', 'Programming', 'Databases', 'ERP', 'Business Intelligence',  'CRM',  'Operating Systems']
tags['Information Technology'] = {'path':'Information Technology', 'tags':_tags}

tags_path = {}
_tags = ['Management Education', 'Engineering Education', 'Competitive Exams']
tags_path['/InnoGems/Academic'] = {'path':'/InnoGems/Academic', 'tags':_tags}

_tags = ['Marketing', 'Finance', 'Human Resources', 'TechOps', 'International', 'BusinessGov', 'Strategy']
tags_path['/InnoGems/Academic/Management Education'] = {'path':'/InnoGems/Academic/Management Education', 'tags':_tags}

_tags = ['Architecture', 'Civil', 'Electrical', 'Electronics', 'Mechanical', 'Computers', 'Instrumentation', 'Production', 'Metallurgy']
tags_path['/InnoGems/Academic/Engineering Education'] = {'path':'/InnoGems/Academic/Engineering Education', 'tags':_tags}

_tags = ['Information Technology']
tags_path['/InnoGems/Professional'] = {'path':'/InnoGems/Professional', 'tags':_tags}

_tags = ['Web Dev', 'Mobile Apps', 'Programming', 'Databases', 'ERP', 'Business Intelligence',  'CRM',  'Operating Systems']
tags_path['/InnoGems/Professional/Information Technology'] = {'path':'/InnoGems/Professional/Information Technology', 'tags':_tags}

_tags = ['Web 2.0 App', 'Web Design']
tags_path['/InnoGems/Professional/Information Technology/Web Dev'] = {'path':'/InnoGems/Professional/Information Technology/Web Dev', 'tags':_tags}

account_types = []
account_types.append('Individual')
account_types.append('Business')
account_types.append('Non-Gov Org')
account_types.append('Gov Org')

channel_types = []
channel_types.append('Professional')
channel_types.append('Academic')
channel_types.append('Social')

def get_account_types():
  return account_types

def get_channel_types():
  return channel_types

def get_channels(category=None):
  #res = memcache.client.get('install.channels.get_channels', None)
  #if res is not None:
  #  return res

  res = []
  try:
    channels_items = channels.get(category).get('channels', [])
    path = channels.get(category).get('path', None)
  except:
    channels_items = []
    path = None

  for channel in channels_items:
    params = {
      'name':channel[0],
      'tags':channel[1],
      'description':channel[2],
      'type':channel[3]
    }
    res.append(params)

  memcache.client.set('install.channels.get_channels', res, api.MEMCACHE_DAY)
  return res, path

def get_tags(category='Root'):
  tags_items = tags.get(category).get('tags', [])
  path = tags.get(category).get('path', None)

  memcache.client.set('install.channels.get_tags', tags_items, api.MEMCACHE_DAY)
  return tags_items, path

def get_tags_by_path(path='/InnoGems'):
  tags_items = tags_path.get(path).get('tags', [])
  path = tags_path.get(path).get('path', None)
  return tags_items, path