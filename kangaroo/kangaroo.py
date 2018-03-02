# Author: Xiaoyong Guo
# Date: 2018-03-01

import json
import os
import sys

from util import (
  BaiduCloudStorage,
  set_timezone_to_shanghai,
  retrieve_managebac_calendar,
  retrieve_baidu_copy_of_calendar,
  calendar_to_list_of_dicts,
  HOMEWORK_ROOT,
)


def update_assignment(baidu_storage, date_str, events):
    date_dir = os.path.join(HOMEWORK_ROOT, date_str)
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


def main():
    set_timezone_to_shanghai()
    cal = retrieve_managebac_calendar()
    baidu_cal = retrieve_baidu_copy_of_calendar()
    if cal == baidu_cal:
        #return
        pass

    baidu_storage = BaiduCloudStorage()
    calendar_path = os.path.join(HOMEWORK_ROOT, 'calendar.ics')
    baidu_storage.upload_bytes(cal.to_ical(), calendar_path)

    event_dict = calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        update_assignment(baidu_storage, date_str, events)
    return 0


if __name__ == '__main__':
    sys.exit(main())
