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

flags.DEFINE_boolean(
    "get_video",
    True,
    "Download videos"
)

flags.DEFINE_boolean(
    "fake_upload_video",
    True,
    "Do not upload videos to Baidu, but generate a shell script to to so."
)

flags.DEFINE_boolean(
    "ignore_downloaded_list",
    True,
    "Do not check downloaded video list."
)

flags.DEFINE_boolean(
    "fake_download_video",
    True,
    "Do not download videos from youtube."
)

flags.DEFINE_boolean(
    "ignore_baidu",
    True,
    "Do not check data in Baidu storage."
)


def update_baidu_homework():
    cal = util.retrieve_managebac_calendar()
    baidu_cal = util.retrieve_baidu_copy_of_calendar()
    if cal == baidu_cal:
        return

    baidu_storage = util.BaiduCloudStorage()
    baidu_storage.upload_bytes(cal.to_ical(), util.BAIDU_CALENDAR_FILE)

    event_dict = util.calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        remote_events = util.retrieve_baidu_homework(date_str)
        if events != remote_events:
            homework_json = json.dumps(events, indent=2)
            baidu_homework_json_file = os.path.join(
                util.HOMEWORK_ROOT, date_str, 'homework.json')
            baidu_storage.upload_bytes(homework_json, baidu_homework_json_file)
            print('remote json file uploaded: %s' % baidu_homework_json_file)


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


def download_youtube_video(fake_download):
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()
    shell_script = '!/usr/bin/bash\n\n'  # if fake_upload is False, not used.

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if event_date >= today:
            to_be_downloaded = util.retrieve_homework_youtube_video_list_by_date(date_str, 'managebac')
            for url in to_be_downloaded:
                video_info = util.download_and_upload_youtube_video(
                    date_str, url,
                    fake_download=fake_download,
                    fake_upload=True)

                filename = video_info['filename']
                remote_filename = os.path.join(util.HOMEWORK_ROOT, date_str, filename)
                shell_script += 'bypy upload "%s" "%s"\n' % (filename, remote_filename)

    with open('baidu_upload.sh', 'wt') as wfile:
        wfile.write(shell_script)


def main(argv):
    flags.FLAGS(argv)
    util.set_timezone_to_shanghai()

    if flags.FLAGS.show:
        show_latest_homework()

    if flags.FLAGS.update_baidu:
        update_baidu_homework()

    if flags.FLAGS.get_video:
        download_youtube_video(flags.FLAGS.fake_download_video)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
