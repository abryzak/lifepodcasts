#!/usr/bin/env python

import getopt
import getpass
import mimetypes
import os
import os.path
import re
import sys

import gdata.sites.client
import gdata.sites.data

SOURCE_APP_NAME = 'abryzak-filePoster-v0.2'

class Poster(object):
  def __init__(self, site_name, domain, parent_name, login_email, login_password):
    self.client = gdata.sites.client.SitesClient(
        source=SOURCE_APP_NAME, site=site_name, domain=domain)
    self.client.ssl = True

    try:
      self.client.ClientLogin(login_email, login_password, source=SOURCE_APP_NAME);
    except gdata.client.BadAuthentication:
      exit('Invalid user credentials given')
    except gdata.client.Error:
      exit('Login Error')

    self.parentEntry = self.FindTopLevelEntry(parent_name)
    if self.parentEntry is None:
      self.parentEntry = self.CreateFileCabinet(parent_name)

  def FindTopLevelEntry(self, name):
    try:
      uri = '%s?path=/%s' % (self.client.MakeContentFeedUri(), name)
      feed = self.client.GetContentFeed(uri=uri)
      if len(feed.entry) > 0:
        return feed.entry[0]
    except Exception, ex:
      exit(ex)

  def CreateFileCabinet(self, parent):
    try:
      return self.client.CreatePage('filecabinet', parent, page_name=parent)

    except Exception, ex:
      exit(ex)

  def FileTitle(self, filename):
    return re.sub(r'[^a-zA-Z0-9_\.\-]+', '', filename)

  def PostFile(self, filepath):
    filename = os.path.basename(filepath)
    title = self.FileTitle(filename)
    file_ex = filename[filename.rfind('.'):]
    if not file_ex in mimetypes.types_map:
      content_type = 'application/octet-stream'
    else:
      content_type = mimetypes.types_map[file_ex]
    try:
      attachment = self.client.UploadAttachment(filepath, self.parentEntry, content_type=content_type, title=title);
      return attachment.GetAlternateLink().href

    except gdata.client.RequestError, ex:
      if ex.status == 409:
        print >> sys.stderr, 'duplicate: %s, finding url' % filename
        return '%s/%s' % (self.parentEntry.GetAlternateLink().href, title)
      else:
        exit(ex)  

    except Exception, ex:
      exit(ex)

def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], '', ['site=', 'domain=', 'parent='])
  except getopt.error, msg:
    exit("""usage: python post_file.py [--site=<name>] [--domain=<name>] [--parent=<parent>] [filename...]""")

  site = 'abryzak'
  domain = None
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
    if option == '--domain':
      domain = arg
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

  poster = Poster(site_name=site, domain=domain, parent_name=parent, login_email=login_email, login_password=login_password)
  for arg in args:
    print poster.PostFile(arg)

if __name__ == '__main__':
  main()
