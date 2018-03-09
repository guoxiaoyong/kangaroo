# Author: Xiaoyong Guo

import datetime
import glob
import io
import json
import os
import sys
import typing

import icalendar
import requests
import pytz
import youtube_dl
import cachetools.func


def get_repo_path():
    path = os.path.abspath(__file__)
    for _ in range(20):
        parent_dir, basename = os.path.split(path)
        if parent_dir == '/':
            raise RuntimeError('repo path not found!')
        elif os.path.exists(os.path.join(parent_dir, '.git')):
            return parent_dir
        else:
            path = parent_dir
    raise RuntimeError('repo path not found!')


# Constants
MANAGEBAC_ICAL_URL = \
    "webcal://fudan.managebac.com/parent/events/child/11748276/token/4fbc3f50-5564-0134-a2c7-0cc47aa8e996.ics"

GET_ICAL_URL = MANAGEBAC_ICAL_URL.replace("webcal", "http")

HOMEWORK_ROOT = os.path.join(get_repo_path(), 'fdis/homework/kangaroo')

STORAGE_CALENDAR_FILE = os.path.join(HOMEWORK_ROOT, 'calendar.ics')


def to_timestamp(datetime_obj: datetime.datetime):
    # Well, not really Unix epoch.
    unix_epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.timezone('Asia/Shanghai'))
    elapsed_time = datetime_obj - unix_epoch
    return elapsed_time.total_seconds()


def to_human_readable_time(datetime_obj: datetime.datetime):
    return datetime_obj.isoformat()


@cachetools.func.ttl_cache(maxsize=1, ttl=60)
def retrieve_managebac_calendar(timeout=20) -> icalendar.Calendar:
    cal_text = requests.get(GET_ICAL_URL, timeout=timeout).text
    cal = icalendar.Calendar.from_ical(cal_text)
    return cal


def calendar_to_list_of_dicts(cal):
    event_dict = dict()
    for component in cal.walk():
        # We are only interested in VEVENT components.
        if component.name != 'VEVENT':
            continue

        event_time = component.get('dtstart').dt  # event start time.
        date_str = event_time.date().strftime('%Y%m%d')
        timestamp = to_timestamp(event_time)
        human_readable_time = to_human_readable_time(event_time)

        summary = component.get('summary')
        if summary is None:
            summary = ""
        else:
            summary = summary.encode().decode()

        description = component.get('description')
        if description is None:
            description = ""
        else:
            description = description.encode().decode()

        event = {
            'summary': summary,
            'description': description,
            'timestamp': timestamp,
            'human_readable_time': human_readable_time,
        }
        if date_str in event_dict:
            event_dict[date_str].append(event)
        else:
            event_dict[date_str] = [event]

    return event_dict


def extract_youtube_video_list_from_description(description: typing.Text):
    url_list = []
    for line in description.split('\n'):
        if 'youtube' in line and 'http' in line:
            url_list.append(line.strip())
    return url_list


def get_homework_json_filepath(date_str: str):
    return os.path.join(HOMEWORK_ROOT, date_str, 'homework.json')


def get_downloaded_video_list_filepath(date_str: str):
    return os.path.join(HOMEWORK_ROOT, date_str, 'downloaded_video.json')


def get_calendar_filepath():
    return os.path.join(HOMEWORK_ROOT, 'calendar.ics')


def force_mkdir(func):
    def update_file(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except FileNotFoundError as exc:
            dirname = os.path.dirname(exc.filename)
            os.makedirs(dirname)
            func(*args, **kwargs)
    return update_file


@force_mkdir
def update_calendar(cal: icalendar.Calendar):
    calendar_path = get_calendar_filepath()
    with open(calendar_path, 'w') as wfile:
        wfile.write(cal.to_ical().decode())


@force_mkdir
def update_homework(homework_list, date_str: str):
    homework_json_file = get_homework_json_filepath(date_str)
    homework_json = json.dumps(homework_list, indent=2)
    with open(homework_json_file, 'w') as wfile:
        wfile.write(homework_json)


@force_mkdir
def update_downloaded(downloaded_list, date_str: str):
    downloaded_json_file = get_downloaded_video_list_filepath(date_str)
    downloaded_json = json.dumps(downloaded_list, indent=2)
    with open(downloaded_json_file, 'w') as wfile:
        wfile.write(downloaded_json)


def download_youtube_video(url: str, ydl_opts=None) -> str:
    if ydl_opts:
        ydl_opts = ydl_opts.copy()
    else:
        ydl_opts = dict()

    postprocessors = [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }]
    ydl_opts.update({
        'writeinfojson': True,
        'prefer_ffmpeg': True,
        'postprocessors': postprocessors,
    })

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Read info file.
    info_json_files = glob.glob('*.info.json')
    assert len(info_json_files) == 1
    with open(info_json_files[0]) as rfile:
        info_dict = json.load(rfile)
        filename = info_dict['_filename']
    os.remove(info_json_files[0])
    assert os.path.isfile(filename), 'Download failed!'
    return filename


def get_youtube_video_filename(url: str) -> str:
    postprocessors = [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }]

    ydl_opts = {
        'forcefilename': True,
        'simulate': True,
        'postprocessors': postprocessors,
        'prefer_ffmpeg': True,
    }

    old_sys_stdout = sys.stdout
    sys.stdout = io.StringIO()
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    stdout_text = sys.stdout.getvalue()
    sys.stdout = old_sys_stdout  # Restore sys.stdout
    for line in reversed(stdout_text.split('\n')):
        line = line.strip()
        if len(line) > 0:
            basename, ext = os.path.splitext(line)
            return "%s.mp4" % basename
    raise RuntimeError('Cannot get video filename!')


def set_timezone_to_shanghai():
    os.environ['TZ'] = 'Asia/Shanghai'
