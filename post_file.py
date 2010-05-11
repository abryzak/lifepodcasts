#!/usr/bin/python

import getopt
import getpass
import mimetypes
import os
import os.path
import sys

import gdata.sites.client
import gdata.sites.data

SOURCE_APP_NAME = 'abryzak-filePoster-v0.1'

class Poster(object):
  def __init__(self, site_name, parent_name, login_email, login_password):
    self.client = gdata.sites.client.SitesClient(
        source=SOURCE_APP_NAME, site=site_name)
    self.client.ssl = True

    try:
      self.client.ClientLogin(login_email, login_password, source=SOURCE_APP_NAME);
    except gdata.client.BadAuthentication:
      exit('Invalid user credentials given')
    except gdata.client.Error:
      exit('Login Error')

    self.parentEntry = None
    self.FindTopLevelEntry(parent_name)
    if self.parentEntry is None:
      self.CreateFileCabinet(parent_name)

  def FindTopLevelEntry(self, name):
    try:
      uri = '%s?path=/%s' % (self.client.MakeContentFeedUri(), name)
      feed = self.client.GetContentFeed(uri=uri)
      if len(feed.entry) > 0:
        self.parentEntry = feed.entry[0];

    except Exception as ex:
      exit(ex)

  def CreateFileCabinet(self, parent):
    try:
      self.parentEntry = self.client.CreatePage('filecabinet', parent, page_name=parent)

    except Exception as ex:
      exit(ex)

  def PostFile(self, filepath):
    try:
      filename = os.path.basename(filepath)
      file_ex = filename[filename.rfind('.'):]
      if not file_ex in mimetypes.types_map:
        content_type = 'application/octet-stream'
      else:
        content_type = mimetypes.types_map[file_ex]
      attachment = self.client.UploadAttachment(filepath, self.parentEntry, content_type=content_type);
      print attachment.GetAlternateLink().href

    except Exception as ex:
      exit(ex)

def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], '', ['site=', 'parent='])
  except getopt.error, msg:
    exit("""usage: python post_file.py [--site=<name>] [filename...]""")

  site = 'abryzak'
  parent = 'files'
  login_email = None
  login_password = None
  if 'GOOGLE_LOGIN' in os.environ:
    login_email = os.environ['GOOGLE_LOGIN']
  if 'GOOGLE_PASSWORD' in os.environ:
    login_password = os.environ['GOOGLE_PASSWORD']

  for option, arg in opts:
    if option == '--site':
      site = arg
    if option == '--parent':
      parent = arg

  if site is None:
    exit('No site provided')
  if parent is None:
    exit('No parent provided')
  if login_email is None:
    exit('No login email provided')
  if login_password is None:
    exit('No login password provided')

  mimetypes.init()

  poster = Poster(site_name=site, parent_name=parent, login_email=login_email, login_password=login_password)
  for arg in args:
    poster.PostFile(arg)

if __name__ == '__main__':
  main()
