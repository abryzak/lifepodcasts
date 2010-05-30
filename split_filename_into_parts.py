#!/usr/bin/env python

import datetime
import os.path
import re
import sys

if len(sys.argv) != 2:
  sys.exit("usage: split_filename_into_parts.py filename")

fn = sys.argv[1]
fn = os.path.basename(fn)
if fn.rfind(".") != -1:
  fn = fn[:fn.rfind(".")]

# grab the service date
match = re.match(r"((?:\d{2,})?\d\d)[-_.](\d\d)[-_.](\d\d)[-_.]", fn)
if match is None:
  sys.exit()
fn = fn[match.end():]
year = match.group(1)
if len(year) == 2:
  year = str(datetime.date.today().year / 100) + year
month = match.group(2)
day = match.group(3)
service_date = datetime.date(int(year), int(month), int(day))
service_date_string = str(service_date.day) + service_date.strftime(" %b %Y")

# grab the service type
match = re.match(r"([^-_.]+)[-_.]", fn)
if match is None:
  sys.exit()
fn = fn[match.end():]
service_type = match.group(1).upper()
service_type_string = None
if service_type == "MSV":
  service_type_string = "Massive"
elif service_type == "PUP":
  service_type_string = "PowerUp"
elif re.match(r"(9(30)?)?AM$", service_type):
  service_type_string = "Morning Service"
elif re.match(r"((6|18)(00)?)?PM$", service_type):
  service_type_string = "Generate"
if service_type_string is None:
  sys.exit()

# grab the speaker
match = re.match(r"([^_]+)[_]", fn)
if match is None:
  sys.exit()
fn = fn[match.end():]
service_speaker = match.group(1)

# the rest is the title
service_title = fn

# now that we have all the parts - output nice versions on each line
print service_date_string
print service_type_string
print service_speaker
print service_title
