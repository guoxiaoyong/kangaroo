# Author: Xiaoyong Guo
# Date: 2018-03-01

import datetime
import json
import os

import requests
import youtube_dl

from icalendar import Calendar


def load_events():
  try:
    events = json.load(open('history.json'))
    return events
  except:
    return []


def store_events(events):
  with open('history.json', 'w') as ofile:
    ofile.write(json.dumps(events, indent=2))


def retrieve_calendar():
  jimcal = 'webcal://fudan.managebac.com/parent/events/child/11748276/token/4fbc3f50-5564-0134-a2c7-0cc47aa8e996.ics'
  url = jimcal.replace('webcal', 'http')
  cal_text = requests.get(url).text
  cal = Calendar.from_ical(cal_text)
  return cal


def get_latest_events(cal):
  today = datetime.datetime.today().date()
  new_events = []
  for component in cal.walk():
    if component.name == 'VEVENT':
      dt = component.get('dtstart').dt
      if dt.date() >= today:
        new_events.append({
            'summary': component.get('summary'),
            'description': component.get('description'),
            'datetime': str(dt)})
  return new_events


def extract_youtube(events):
  url_list = []
  for event in events:
    if not event['description']:
      continue
    for line in event['description'].split('\n'):
      if 'youtube' in line and 'http' in line:
        url_list.append(line.strip())
  return url_list

def download_video(url):
  with youtube_dl.YoutubeDL() as ydl:
    ydl.download(url)

def main():
  os.environ['TZ'] = 'Asia/Shanghai'
  cal = retrieve_calendar()
  events = get_latest_events(cal)
  url_list = extract_youtube(events)
  for url in url_list:
    print(url)
    #print('download ' + url)
    #download_video([url])


if __name__ == '__main__':
  main()
