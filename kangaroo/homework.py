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

flags.DEFINE_string(
    "storage_name",
    'local',
    "Storage name."
)

flags.DEFINE_boolean(
    "update_storage",
    True,
    "Update homework in storage."
)

flags.DEFINE_boolean(
    "get_video",
    True,
    "Download videos"
)


def one_day_events_to_text(events):
    text = []
    for event in events:
        if 'ES Menu' in event['summary']:
            continue
        text.append('='*16)
        text.append('Date time: %s' % event['human_readable_time'])
        text.append('Summary: %s' % event['summary'])
        text.append('Description:\n%s\n\n' % event['description'])
    return '\n'.join(text)


def get_latest_homework():
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()
    text_list = []
    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if event_date >= today:
            text = one_day_events_to_text(events)
            text_list.append(text)
    return '\n'.join(text_list)


def update_storage_homework(storage_name, force=False):
    cal = util.retrieve_managebac_calendar()
    storage_cal = util.retrieve_storage_calendar(storage_name)
    if force or cal == storage_cal:
        return

    storage_ops = util.get_storage_ops(storage_name)
    storage_ops.update_calendar(cal.to_ical())

    event_dict = util.calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        remote_events = storage_ops.retrieve_homework_dict(date_str)
        if events != remote_events:
            storage_ops.update_homework(events, date_str)


def download_and_upload_youtube_video(ignore_downloaded_list, fake_download, fake_upload):
    if ignore_downloaded_list:
        cal = util.retrieve_managebac_calendar()
    else:
        cal = util.retrieve_baidu_copy_of_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()
    shell_script = '!/usr/bin/bash\n\n'  # if fake_upload is False, not used.

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if event_date >= today:
            if ignore_downloaded_list:
                to_be_downloaded = util.retrieve_homework_youtube_video_list_by_date(date_str)
                downloaded_video_list = []
            else:
                to_be_downloaded, downloaded_video_list = util.get_videos_to_be_downloaded(date_str)
            # Download videos, upload maybe fake
            for url in to_be_downloaded:
                new_info = util.download_and_upload_youtube_video(
                    date_str, url,
                    fake_download=fake_download,
                    fake_upload=fake_upload)
                downloaded_video_list.append(new_info)
            util.update_downloaded_video_list(downloaded_video_list, date_str)

            # Generate upload command, useless if fake_upload is false.
            for video_info in downloaded_video_list:
                if video_info['url'] in to_be_downloaded:
                    filename = video_info['filename']
                    remote_filename = os.path.join(util.HOMEWORK_ROOT, date_str, filename)
                    shell_script += 'bypy upload "%s" "%s"\n' % (filename, remote_filename)

    # Write to shell script file.
    if fake_upload:
        with open('baidu_upload.sh', 'wt') as wfile:
            wfile.write(shell_script)


def download_youtube_video(storage_name):
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()
    storage_ops = util.get_storage_ops(storage_name)

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if event_date >= today:
            to_be_downloaded, downloaded_video_list = \
                storage_ops.get_videos_to_be_downloaded(date_str)
            for url in to_be_downloaded:
                video_info = util.download_and_upload_youtube_video(
                    storage_name, date_str, url)
                downloaded_video_list.append(video_info)
            # update download_video_list
            storage_ops.update_downloaded(downloaded_video_list, date_str)



def main(argv):
    flags.FLAGS(argv)
    util.set_timezone_to_shanghai()

    if flags.FLAGS.show:
        print(get_latest_homework())

    if flags.FLAGS.update_storage:
        update_storage_homework(flags.FLAGS.storage_name)

    if flags.FLAGS.get_video:
        download_youtube_video(flags.FLAGS.storage_name)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
