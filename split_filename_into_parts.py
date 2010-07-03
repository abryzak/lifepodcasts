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

def normalise_value(value, normalised_regexes):
  # we always want to remove extraneous whitespace
  value = re.sub(r' {2,}', ' ', value.strip(' '))
  for normalised_value in normalised_regexes:
    for regex in normalised_regexes[normalised_value]:
      if re.match(r"^ ?"+regex+r" ?$", value, re.I):
        return normalised_value
  return value

# grab the service type
match = re.match(r"([^-_.]+)[-_.]", fn)
if match is None:
  sys.exit()
fn = fn[match.end():]
normalised_service_types = {
  'Massive': ['massive', 'msv'],
  'PowerUp': ['powerup', 'pup'],
  'Morning Service': [r'(9(30)?)?am'],
  'Generate': [r'gen(erate)?', r'(6(00)?)?pm'],
}
service_type = normalise_value(match.group(1), normalised_service_types)

# grab the speaker
match = re.match(r"([^_]+)[_]", fn)
if match is None:
  sys.exit()
fn = fn[match.end():]
normalised_speakers = {
  'Ps Ben Higgins': [r'(ps ?)?b(en)? ?higg[ie]ns?'],
  'Ps Geoff Blight': [r'(ps ?)?(g(eoff)?|j(eff)?) ?blight'],
  'Ps Lee Blight': [r'(ps ?)?l(ee)? ?blight'],
  'Ps Sacha Pace': [r'(ps ?)?s(a[cs]ha)? ?pace'],
}
service_speaker = normalise_value(match.group(1), normalised_speakers)

# the rest is the title
service_title = fn
service_title = re.sub(r' {2,}', ' ', service_title.strip(' '))
service_title = re.sub(r'^- ?', '', service_title)

# now that we have all the parts - output nice versions on each line
print service_date_string
print service_type
print service_speaker
print service_title
