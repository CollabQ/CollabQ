# Copyright 2010 http://www.collabq.com
# To change this template, choose Tools | Templates
# and open the template in the editor.
from common import api

def get_breadcrumb(view, tagkey):
  breadcrumb = []
  tag_current = api.channel_get_tag(view, tagkey)
  breadcrumb.append(tag_current)
  if tagkey != '/tag_country/Global':
    for i in range(2):
      tag_current = api.channel_get_tag(view, tag_current.path)
      if tag_current:
        breadcrumb.insert(0, tag_current)
      else:
        break
  return breadcrumb