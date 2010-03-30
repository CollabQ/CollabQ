# Copyright 2010 http://www.collabq.com
import datetime
import time

def utcnow():
  return datetime.datetime.utcnow()

def utcnow_ts():
  return time.mktime(utcnow())
