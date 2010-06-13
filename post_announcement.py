#!/usr/bin/env python

import getopt
import getpass
import os
import os.path
import re
import sys

import gdata.sites.client
import gdata.sites.data

SOURCE_APP_NAME = 'abryzak-announcementPoster-v0.2'

class AnnouncementPoster(object):
  def __init__(self, site_name, domain, login_email, login_password):
    self.client = gdata.sites.client.SitesClient(
        source=SOURCE_APP_NAME, site=site_name, domain=domain)
    self.client.ssl = True

    try:
      self.client.ClientLogin(login_email, login_password, source=SOURCE_APP_NAME);
    except gdata.client.BadAuthentication:
      exit('Invalid user credentials given')
    except gdata.client.Error:
      exit('Login Error')

    self.announcementsPageEntry = self.FindAnnouncementsPageEntry()
    if self.announcementsPageEntry is None:
      self.announcementsPageEntry = self.CreateAnnouncementsPage()

  def FindAnnouncementsPageEntry(self):
    try:
      uri = '%s?kind=%s' % (self.client.MakeContentFeedUri(), 'announcementspage')
      feed = self.client.GetContentFeed(uri=uri)
      if len(feed.entry) > 0:
        return feed.entry[0]
    except Exception, ex:
      exit(ex)

  def CreateAnnouncementsPage(self):
    try:
      return self.client.CreatePage('announcementspage', 'Announcements')

    except Exception, ex:
      exit(ex)

  def PageName(self, title):
    return re.sub(r'[^a-zA-Z0-9_\-]+', '', title)

  def PostAnnouncement(self, title, html):
    page_name = self.PageName(title)
    try:
      attachment = self.client.CreatePage('announcement', title, html=html, parent=self.announcementsPageEntry, page_name=page_name);
      return attachment.GetAlternateLink().href

    except gdata.client.RequestError, ex:
      if ex.status == 409:
        print >> sys.stderr, 'duplicate: %s, finding url' % title
        return '%s/%s' % (self.announcementsPageEntry.GetAlternateLink().href, page_name)
      else:
        exit(ex)  

    except Exception, ex:
      exit(ex)

def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], '', ['site='])
  except getopt.error, msg:
    exit("""usage: python post_announcement.py [--site=<name>] [--domain=<name>] title""")

  site = 'abryzak'
  domain = None
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

  if site is None:
    exit('No site provided')
  if login_email is None:
    exit('No login email provided')
  if login_password is None:
    exit('No login password provided')

  poster = AnnouncementPoster(site_name=site, domain=domain, login_email=login_email, login_password=login_password)
  html=''
  for data in sys.stdin.read():
    html = html + data
  print poster.PostAnnouncement(args[0], html)

if __name__ == '__main__':
  main()
