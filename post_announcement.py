#!/usr/bin/python

import getopt
import getpass
import mimetypes
import os
import os.path
import sys

import gdata.sites.client
import gdata.sites.data


SOURCE_APP_NAME = 'lifeChurch-betterPodcasting-v0.1'


class AnnouncementPoster(object):
  def __init__(self, site_name=None, login_email=None, login_password=None):
    if site_name is None:
      site_name = self.PromptSiteName()
    
    if login_email is None:
      login_email = self.PromptLoginEmail()
    
    if login_password is None:
      login_password = self.PromptLoginPassword(login_email)

    self.client = gdata.sites.client.SitesClient(
        source=SOURCE_APP_NAME, site=site_name)
    self.client.ssl = True

    try:
      self.client.ClientLogin(login_email, login_password, source=SOURCE_APP_NAME);
    except gdata.client.BadAuthentication:
      exit('Invalid user credentials given.')
    except gdata.client.Error:
      exit('Login Error')

  def PromptSiteName(self):
    site_name = ''
    while not site_name:
      site_name = raw_input('site name: ')
      if not site_name:
        print 'Please enter the name of your Google Site.'
    return site_name

  def PromptLoginEmail(self):
    return raw_input('login email: ')

  def PromptLoginPassword(self, login_email):
    return getpass.getpass('enter password for user %s:' % login_email)

  def PostFile(self, filepath):
    try:
      filename = os.path.basename(filepath)
      file_ex = filename[filename.rfind('.'):]
      if not file_ex in mimetypes.types_map:
        content_type = 'application/octet-stream'
      else:
        content_type = mimetypes.types_map[file_ex]
      uri = '%s?kind=%s' % (self.client.MakeContentFeedUri(), 'announcementspage')
      feed = self.client.GetContentFeed(uri=uri)
      entry = self.client.CreatePage('announcement', filename, parent=feed.entry[0]);
      print 'Created page. View it at %s: ' % entry.GetAlternateLink().href
      attachment = self.client.UploadAttachment(filepath, entry, content_type=content_type);
      print 'Uploaded file. View it at %s: ' % attachment.GetAlternateLink().href

    except gdata.client.RequestError, error:
      print >> sys.stderr, error


def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], '', ['site='])
  except getopt.error, msg:
    print >> sys.stderr, """python post_announcement.py [--site=SITE] [FILE]..."""
    sys.exit(2)

  site = 'lifechurchpodcasts'
  login_email = None
  login_password = None
  if 'GOOGLE_LOGIN' in os.environ:
    login_email = os.environ['GOOGLE_LOGIN']
  if 'GOOGLE_PASSWORD' in os.environ:
    login_password = os.environ['GOOGLE_PASSWORD']

  for option, arg in opts:
    if option == '--site':
      site = arg
  
  mimetypes.init()

  poster = AnnouncementPoster(site_name=site, login_email=login_email, login_password=login_password)
  for arg in args:
    poster.PostFile(arg)


if __name__ == '__main__':
  main()
