# Author: Xiaoyong Guo

import atexit
import datetime
import errno
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import typing

import icalendar
import requests
import pytz
import youtube_dl
import cachetools.func


# Constants
MANAGEBAC_ICAL_URL = \
    "webcal://fudan.managebac.com/parent/events/child/11748276/token/4fbc3f50-5564-0134-a2c7-0cc47aa8e996.ics"

GET_ICAL_URL = MANAGEBAC_ICAL_URL.replace("webcal", "http")

HOMEWORK_ROOT = 'fdis/homework/kangaroo'

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


def retrieve_storage_calendar(storage_name: str) -> icalendar.Calendar:
    storage = get_storage(storage_name)
    cal_text = storage.load(STORAGE_CALENDAR_FILE)
    if cal_text:
        cal = icalendar.Calendar.from_ical(cal_text)
    else:
        cal = icalendar.Calendar()
    return cal


def retrieve_calendar(name: str):
    if name == 'managebac':
        cal = retrieve_managebac_calendar()
    else:
        cal = retrieve_storage_calendar(name)
    return calendar_to_list_of_dicts(cal)


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


class StorageOps(object):
    def __init__(self, storage_name):
        self._storage = get_storage(storage_name)

    @property
    def storage_name(self):
        return self._storage.name

    @staticmethod
    def get_homework_json_filepath(date_str: str):
        return os.path.join(HOMEWORK_ROOT, date_str, 'homework.json')

    @staticmethod
    def get_downloaded_video_list_filepath(date_str: str):
        return os.path.join(HOMEWORK_ROOT, date_str, 'downloaded_video.json')

    @staticmethod
    def get_calendar_filepath():
        return os.path.join(HOMEWORK_ROOT, 'calendar.ics')

    def retrieve_homework_dict(self, date_str):
        homework_json_file = self.get_homework_json_filepath(date_str)
        if not self._storage.file_exists(homework_json_file):
            return dict()

        homework_json = self._storage.load(homework_json_file)
        try:
            homework_dict = json.loads(homework_json)
        except json.decoder.JSONDecodeError:
            homework_dict = {}
        return homework_dict

    def get_homework_video_list(self, date_str: str):
        homework_dict = self.retrieve_homework_dict(date_str)
        video_list = []
        for video_info in homework_dict:
            description = video_info.get('description', '')
            video_list += extract_youtube_video_list_from_description(description)
        return video_list

    def retrieve_downloaded_video_list(self, date_str: str):
        video_json_file = self.get_downloaded_video_list_filepath(date_str)
        if not self._storage.file_exists(video_json_file):
            return []

        video_json = self._storage.load(video_json_file)
        video_dict = json.loads(video_json)
        #
        # video_dict structure:
        # [
        #   {
        #     'url': 'https://www.yutube.com/ABCDEFD'
        #     'filename': 'Video File Name.ABCDEF.mp4'
        #   },
        # ]
        return video_dict

    def get_videos_to_be_downloaded(self, date_str: str):
        downloaded_video_list = self.retrieve_downloaded_video_list(date_str)
        downloaded_video_set = {video['url'] for video in downloaded_video_list}
        homework_video_set = set(self.get_homework_video_list(date_str))
        return (homework_video_set - downloaded_video_set,
                downloaded_video_list)

    def update_calendar(self, ical_text):
        calendar_path = self.get_calendar_filepath()
        self._storage.upload_contents(ical_text, calendar_path)

    def update_homework(self, homework_dict, date_str: str):
        homework_json_file = self.get_homework_json_filepath(date_str)
        homework_json = json.dumps(homework_dict, indent=2)
        self._storage.upload_contents(homework_json, homework_json_file)

    def update_downloaded(self, downloaded_list, date_str: str):
        downloaded_json_file = self.get_downloaded_video_list_filepath(date_str)
        downloaded_json = json.dumps(downloaded_list, indent=2)
        self._storage.upload_contents(downloaded_json, downloaded_json_file)


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
    ydl_opts = {
        'forcefilename': True,
        'simulate': True,
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
            return line
    raise RuntimeError('Cannot get video filename!')


def download_and_upload_youtube_video(storage_name: str, date_str: str, url: str) -> dict:

    filename = download_youtube_video(url)

    if not os.path.isfile(filename):
        raise FileNotFoundError(filename)

    remote_filename = os.path.join(HOMEWORK_ROOT, date_str, os.path.basename(filename))
    storage = get_storage(storage_name)
    storage.upload(filename, remote_filename)
    if not storage.file_exists(remote_filename):
        raise RuntimeError('upload %s failed!' % remote_filename)

    return {
        'url': url,
        'filename': filename,
    }


def set_timezone_to_shanghai():
    os.environ['TZ'] = 'Asia/Shanghai'


class LocalStorage(object):
    _name = 'local'

    def __init__(self, rootdir=None):
        if rootdir is None:
            self._rootdir = os.path.expanduser('~/.kangaroo')
            if os.path.isdir(self._rootdir):
                pass
            elif os.path.isfile(self._rootdir):
                raise ValueError('rootdir should be a directory')
            else:
                os.mkdir(self._rootdir)
        else:
            assert os.path.exists(rootdir)
            self._rootdir = rootdir

    @property
    def name(self):
        return type(self)._name

    def _fullpath(self, path):
        return os.path.join(self._rootdir, path)

    def load(self, filepath: str):
        filepath = self._fullpath(filepath)
        if os.path.isfile(filepath):
            with open(filepath, 'rb') as rfile:
                content = rfile.read()
            return content
        return b''

    def upload(self, filename: str, remotepath: str = ''):
        if remotepath.endswith('/') or remotepath == '':
            remotepath += os.path.basename(filename)
        remotepath = self._fullpath(remotepath)

        parent_dir, _ = os.path.split(remotepath)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)

        if os.path.isfile(filename):
            shutil.copyfile(filename, remotepath)
        else:
            raise FileNotFoundError(filename)

    def upload_bytes(self, contents, remotepath: str):
        if isinstance(contents, str):
            contents = contents.encode()

        with ScopedTempDir() as temp_dir:
            local_file = os.path.join(temp_dir, 'tempfile')
            with open(local_file, 'wb') as wfile:
                wfile.write(contents)
            assert os.path.isfile(local_file), '%s not found!' % local_file
            self.upload(local_file, remotepath)

    def upload_contents(self, contents, remote_path: str):
        self.upload_bytes(contents, remote_path)

    def download(self, filepath: str, localpath: str = ''):
        if localpath.endswith('/') or localpath == '':
            localpath += os.path.basename(filepath)
        shutil.copyfile(self._fullpath(filepath), localpath)

    def download_as_bytes(self, filepath: str):
        if not self.file_exists(filepath):
            return b''

        with ScopedTempDir() as temp_dir:
            local_file = os.path.join(temp_dir, 'tempfile')
            self.download(filepath, local_file)
            with open(local_file, 'rb') as rfile:
                contents = rfile.read()
        return contents

    def file_exists(self, filepath):
        filepath = self._fullpath(filepath)
        return os.path.exists(filepath)

    def makedir(self, dir_name: str) -> None:
        try:
            os.makedirs(self._fullpath(dir_name))
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(self._fullpath(dir_name)):
                pass
            else:
                raise
