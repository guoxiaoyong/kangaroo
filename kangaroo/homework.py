# Author: Xiaoyong Guo
# Date: 2018-03-01

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


def update_repo_homework():
    cal = util.retrieve_managebac_calendar()
    util.update_calendar(cal)

    event_dict = util.calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        util.update_homework(events, date_str)


def download_youtube_video(specified_date_str=None):
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    today = datetime.datetime.today().date()

    def condition(date):
        if specified_date_str:
            return specified_date_str == date.strftime('%Y%m%d')
        else:
            return date >= today

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if condition(event_date):
            to_be_downloaded = util.extract_youtube_video_list_from_description(events['description'])
            downloaded_list = []
            for url in to_be_downloaded:
                filename = util.download_youtube_video(url)
                video_info = {
                    'url': url,
                    'filename': filename,
                }
                downloaded_list.append(video_info)
            util.update_downloaded(downloaded_list, date_str)


def main(argv):
    flags.FLAGS(argv)
    util.set_timezone_to_shanghai()
    update_repo_homework()

    if flags.FLAGS.show:
        print(get_latest_homework())

    if flags.FLAGS.get_video:
        download_youtube_video(flags.FLAGS.storage_name)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
