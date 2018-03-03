# Author: Xiaoyong Guo
# Date: 2018-03-01

import json
import os
import sys
import datetime

import absl.flags as flags

import util

flags.DEFINE_boolean(
    "show",
    True,
    "Show latest homework or events."
)

flags.DEFINE_boolean(
    "update_baidu",
    False,
    "Update homework in Baidu cloud storage."
)


def update_assignment(baidu_storage, date_str, events):
    date_dir = os.path.join(util.HOMEWORK_ROOT, date_str)
    remote_json_file = os.path.join(date_dir, 'homework.json')
    baidu_storage.makedir(date_dir)  # Will create dir if not exist.
    remote_json = baidu_storage.download_as_bytes(remote_json_file)
    try:
        remote_events = json.loads(remote_json)
    except json.decoder.JSONDecodeError:
        remote_events = dict()

    if events != remote_events:
        homework_json = json.dumps(events, indent=2)
        baidu_storage.upload_bytes(homework_json, remote_json_file)
        print('remote json file uploaded: %s' % remote_json_file)


def update_baidu_homework():
    cal = util.retrieve_managebac_calendar()
    baidu_cal = util.retrieve_baidu_copy_of_calendar()
    if cal == baidu_cal:
        return

    baidu_storage = util.BaiduCloudStorage()
    baidu_storage.upload_bytes(cal.to_ical(), util.BAIDU_CALENDAR_FILE)

    event_dict = util.calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        update_assignment(baidu_storage, date_str, events)


def one_day_events_to_text(events):
    text = ''
    for event in events:
        text += 'Date time: %s\n' % event['human_readable_time']
        text += 'Summary: %s\n' % event['summary']
        text += 'Description:\n%s\n' % event['description']
    return text


def show_latest_homework():
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()
    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if event_date >= today:
            text = one_day_events_to_text(events)
            print('='*16)
            print(text)


def main(argv):
    flags.FLAGS(argv)
    util.set_timezone_to_shanghai()

    if flags.FLAGS.show:
        show_latest_homework()

    if flags.FLAGS.update_baidu:
        update_baidu_homework()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
