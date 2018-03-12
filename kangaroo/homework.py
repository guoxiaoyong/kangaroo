# Author: Xiaoyong Guo
# Date: 2018-03-01

import sys
import datetime
from typing import Union

import absl.flags as flags

import util

flags.DEFINE_boolean(
    "get_video",
    False,
    "Download videos"
)

flags.DEFINE_string(
    "date",
    None,
    "date"
)


def get_latest_date(next_day: int = 1):
    today = datetime.datetime.today().date()
    return today + datetime.timedelta(days=next_day)


def one_day_events_to_text(events):
    text = []
    for event in events:
        if 'ES Menu' in event['summary']:
            continue
        text.append('=' * 16)
        text.append('Date time: %s' % event['human_readable_time'])
        text.append('Summary: %s' % event['summary'])
        text.append('Description:\n%s\n\n' % event['description'])
    return '\n'.join(text)


def get_latest_homework(specified_date_str: Union[str, None] = None):
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    latest_date = get_latest_date()
    text_list = []

    def condition(date):
        if specified_date_str:
            return specified_date_str == date.strftime('%Y%m%d')
        else:
            return date >= latest_date

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if condition(event_date):
            text = one_day_events_to_text(events)
            text_list.append(text)
    return '\n'.join(text_list)


def update_repo_homework():
    cal = util.retrieve_managebac_calendar()
    util.update_calendar(cal)

    event_dict = util.calendar_to_list_of_dicts(cal)
    for date_str, events in event_dict.items():
        util.update_homework(events, date_str)


def download_youtube_video(
        specified_date_str: Union[str, None] = None,
        download: bool = True):
    cal = util.retrieve_managebac_calendar()
    event_dict = util.calendar_to_list_of_dicts(cal)
    latest_date = get_latest_date()

    def condition(date):
        if specified_date_str:
            return specified_date_str == date.strftime('%Y%m%d')
        else:
            return date >= latest_date

    for date_str, events in event_dict.items():
        event_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        if condition(event_date):
            to_be_downloaded = []
            for event in events:
                to_be_downloaded.extend(util.extract_youtube_video_list_from_description(event['description']))
            downloaded_list = []
            for url in to_be_downloaded:
                if download:
                    filename = util.download_youtube_video(url)
                else:
                    filename = util.get_youtube_video_filename(url)
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
    print(get_latest_homework(flags.FLAGS.date))

    if flags.FLAGS.get_video:
        download_youtube_video(flags.FLAGS.date)
    else:
        download_youtube_video(flags.FLAGS.date, download=False)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
