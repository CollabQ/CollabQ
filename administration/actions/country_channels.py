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

from common import api
from common import exception
from common import util
from common.models import Actor, Relation, ChannelTag


def init_tags():
  #Top tags
  #"""
  tag_ref = ChannelTag(term='Global', taxonomy='tag_country', path='/tag_geo')
  key_global = tag_ref.put()
  
  #Regions
  regions      = ['Africa','Asia','Central America and Caribbean',
                  'Europe','Middle East and North Africa','North America',
                  'Oceania','Polar Regions','South America']
                  
  regions_keys = build_tags(regions, 'tag_geo', '/tag_geo')
  
  #"""
  """
  query = Relation.gql('WHERE owner=:1', '/tag_geo')
  regions = query.fetch(9999)
  countries_tags = []

  for region in regions:
    query = Relation.gql('WHERE relation=:1 and owner=:2', 'tags_hierarchical', region.target)
    countries_tags.extend(query.fetch(9999))

  for country in countries_tags:
    country_ref = Relation(owner='/tag_geo/Global', relation='tags_hierarchical', target=country.target)
    country_ref.put()

  query = Relation.gql('WHERE owner=:1 and relation=:2', '/tag_geo/Global', 'tags_hierarchical')
  countries = query.fetch(9999) #"""

  util.set_metadata('DEFAULT_TAG', '/tag_geo/Global')
  util.set_metadata('ROOT_TAG', '/tag_geo')

  return regions #, countries

def build_tags(tags, taxonomy, path):
  keys = []
  for tag in tags:
    #creating tag
    logging.info('Creating Tag %s' % (tag))
    tag_ref = ChannelTag(term=tag, taxonomy=taxonomy, path=path)
    key = tag_ref.put()

    #creating relation
    if(path != key.name()):
      rel_ref = Relation(owner=path, relation='tags_hierarchical', target=key.name())
      rel_ref = rel_ref.put()
      logging.info("Relation: %s -> %s" % (path, key.name()))

    keys.append(key)
    logging.info("India: %s" % key.name())

  return keys

def build_channels(api_user, nick, channels, path, taxonomy, country=False):
  res = []
  tags = build_tags(channels, taxonomy, path)
  for channel in channels:
    tags = [path, path+'/'+channel]
    if(country):
      rel_ref = Relation(owner='/tag_geo/Global', relation='tags_hierarchical', target=path+'/'+channel)
      rel_ref = rel_ref.put()
      tags.append('/tag_geo/Global')
    description = 'Group P.O.Box for %s' % channel
    try:
      channel_ref = api.channel_create(api_user, nick=nick, channel=channel.title().replace(' ', ''), tags=tags, description=description)
    except exception.ApiException:
      logging.info('Channel Exists')
      nick = api.clean.channel(channel.title().replace(' ', ''))
      query = Actor.gql('WHERE nick=:1', nick)
      channel_ref = query.get()
      if channel_ref:
        if not path in channel_ref.tags:
          channel_ref.tags.append(path)
          channel_key = channel_ref.put()

    res.append(channel_ref)
  logging.info('End Creating Channels')
  return res

def channel_create_with_tags(page):
  logging.info('channel_create_with_tags')
  logging.info('page: %s' % page)
  items = {}
  #South America
  path = '/tag_geo/South America'
  countries = ['Argentina','Bolivia','Brazil','Chile','Colombia','Ecuador','Falkland Islands','French Guiana','Guyana','Paraguay','Peru','Suriname','Uruguay','Venezuela']
  items['1']=[path,countries, True]

  #Noth America
  path = '/tag_geo/North America'
  countries = ['Bermuda','Canada','Greenland','Mexico','Saint Pierre and Miquelon','United States']
  items['2']=[path,countries, True]

  #Central America amp Caribbean
  path = '/tag_geo/Central America and Caribbean'
  countries = ['Anguilla','Antigua and Barbuda','Aruba','Bahamas','Barbados','Belize','British Virgin Islands','Cayman Islands','Costa Rica','Cuba','Dominica','Dominican Republic','El Salvador','Grenada','Guadeloupe','Guatemala','Haiti','Honduras','Jamaica','Martinique','Montserrat','Navassa Island']
  items['3']=[path,countries, True]

  countries = ['Netherlands Antilles','Nicaragua','Panama','Puerto Rico','Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines','Trinidad and Tobago','Turks and Caicos Islands','United States Virgin Islands']
  items['4']=[path,countries, True]

  #Africa
  path = '/tag_geo/Africa'
  countries = ['Algeria', 'Angola', 'Bassas da India', 'Benin', 'Botswana','Burkina Faso','Burundi','Cameroon','Cape Verde','Central African Republic','Chad','Comoros','Congo','Congo DR','Cote DIvoire','Djibouti','Egypt','Equatorial Guinea','Eritrea','Ethiopia','Europa Island','Gabon','Gambia']
  items['5']=[path,countries, True]

  countries = ['Ghana','Glorioso Islands','Guinea','Guinea Bissau','Juan de Nova Island','Kenya','Lesotho','Liberia','Libya','Madagascar','Malawi','Mali','Mauritania','Mauritius','Mayotte','Morocco','Mozambique','Namibia','Niger','Nigeria','Reunion','Rwanda','Saint Helena','Sao Tome and Principe']
  items['6']=[path,countries, True]

  countries = ['Senegal','Seychelles','Sierra Leone','Somalia','South Africa','Sudan','Swaziland','Tanzania','Togo','Tromelin Island','Tunisia','Uganda','Western Sahara','Zambia','Zimbabwe']
  items['7']=[path,countries, True]

  # Middle East and North Africa
  path = '/tag_geo/Middle East and North Africa'
  countries = ['Algeria','Bahrain','Cyprus','Djibouti','Egypt','Eritrea','Ethiopia','Iran','Iraq','Israel','Jordan','Kuwait','Lebanon','Libya','Mauritania','Morocco','Oman','Palestine','Qatar','Saudi Arabia','Somalia','Sudan','Syria','Tunisia','Turkey','United Arab Emirates','Western Sahara','Yemen']
  items['8']=[path,countries, True]

  #Asia
  path = '/tag_geo/Asia'
  countries = ['Afghanistan','Armenia','Azerbaijan','Bahrain','Bangladesh','Bhutan','British Indian Ocean Territory','Brunei','Cambodia','China', 'Cyprus','Hong Kong','India','Indonesia','Iran','Iraq','Israel','Japan','Jordan','Kazakhstan','Kuwait','Kyrgyzstan','Laos','Lebanon','Macau','Malaysia','Maldives', 'Mongolia']
  items['9']=[path,countries, True]

  countries = ['Myanmar','Nepal','North Korea','Oman','Pakistan','Palestine','Paracel Islands','Philippines','Qatar','Russia','Saudi Arabia','Singapore','South Korea','Sri Lanka','Syria','Taiwan','Tajikistan','Thailand','Timor Leste','Turkey','Turkmenistan','United Arab Emirates','Uzbekistan','Vietnam','Yemen']
  items['10']=[path,countries, True]

  #Europe
  path = '/tag_geo/Europe'
  countries = ['Albania','Andorra','Austria','Belarus','Belgium','Bosnia and Herzegovina','Bulgaria','Croatia','Czech Republic','Denmark','Estonia','Faroe Islands','Finland','France','Germany','Gibraltar','Greece','Guernsey','Holy See','Hungary','Iceland']
  items['11']=[path,countries, True]

  countries = ['Ireland','Isle of Man','Italy','Jersey','Kosovo','Latvia','Liechtenstein']
  items['12']=[path,countries, True]

  countries = ['Lithuania','Luxembourg','Macedonia','Malta','Moldova','Monaco','Montenegro','Netherlands','Norway','Poland','Portugal','Romania']
  items['13']=[path,countries, True]

  countries = ['San Marino','Serbia','Slovakia','Slovenia','Spain','Svalbard and Jan Mayen Islands','Sweden','Switzerland','Ukraine','United Kingdom']
  items['14']=[path,countries, True]


  ###### Cities #####
  path = '/tag_geo/South America/Bolivia'
  countries = ['Chuquisaca','Cochabamba','Beni','La Paz','Oruro','Pando','Potosi','Santa Cruz','Tarija']
  items['15']=[path,countries, False]

  path = '/tag_geo/North America/United States'
  countries = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','District of Columbia','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri']
  items['16']=[path,countries, False]

  path = '/tag_geo/North America/United States'
  countries = ['Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']
  items['17']=[path,countries, False]

  path = '/tag_geo/Asia/India'
  countries = ['Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu and Kashmir', 'Jharkhand', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Orissa', 'Pondicherry']
  items['18']=[path,countries, False]

  path = '/tag_geo/Asia/India'
  countries = ['Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal']
  items['19']=[path,countries, False]

  path = '/tag_geo/Asia/India/Andhra Pradesh'
  countries = ['Hyderabad','Mahbubnagar','Rangareddy','Adilabad','Warangal','Karimnagar','Nalgonda','Nizamabad','Khammam','Anantapur','Chittoor','Kadapa','Kurnool','East Godavari','Krishna','Nellore','Prakasam','Srikakulam','Visakhapatnam','Vizianagaram','West Godavari']
  items['20']=[path,countries, False]

  if page < 21:
    path = items.get(str(page))[0]
    countries = items.get(str(page))[1]
    is_country = items.get(str(page))[2]
    build_channels(api.ROOT, api.ROOT.nick, countries, path, 'tag_geo', is_country)
  else:
    init_tags()
    countries = "Continents"

  return countries

def process(page, limit, offset):
  logging.info('process')
  logging.info('page: %s, limit: %s, offset: %s' % (page, limit, offset))
  redirect = page < 21
  return redirect, channel_create_with_tags(page)