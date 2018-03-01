# Author: Xiaoyong Guo
# Date: 2018-03-01

import sys
import json

from .util import (
  BaiduCloudStorage,
  set_timezone_to_shanghai,
  ScopedTempDir,
  retrieve_managebac_calendar,
  calendar_to_list_of_dicts,
)


def update_assignment(baidu_storage, date_str, events):
    filepath = os.path.join('kangaroo', date_str)
    baidu_storage.makedir(filepath)
    homework_json = json.dumps(event, indent=2)
    with ScopedTempDir(suffix='kangaroo_') as temp_dir:
        json_local = os.path.join(temp_dir, 'homework.json')
        json_remote = os.path.join(filepath, 'homework.json')
        with open(json_local, 'wt') as wfile:
            wfile.write(homework_json)

        video_list_local = os.path.join(temp_dir, 'video_list.json')
        video_list_remote = os.path.join(filepath, 'video_list.json')
        with open(video_list, 'wt') as wfile:
            wfile.write(json_local)

    baidu_storage.upload(json_local, json_remote)
    baidu_storage.upload(video_list_local, video_list_remote)


def main():
    set_timezone_to_shanghai()
    cal = retrieve_managebac_calendar()
    event_dict = calendar_to_list_of_dicts(cal)
    baidu_storage = BaiduCloudStorage()
    for date_str, events in event_dict:
        update_assignment(baidu_storage, date_str, events)
    return 0


if __name__ == '__main__':
    sys.exit(main())
