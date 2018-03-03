# Author: Xiaoyong Guo

import atexit
import datetime
import errno
import json
import os
import shutil
import tempfile
import typing

import bypy
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

BAIDU_CALENDAR_FILE = os.path.join(HOMEWORK_ROOT, 'calendar.ics')


def to_timestamp(datetime_obj: datetime.datetime):
    # Well, not really Unix epoch.
    unix_epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.timezone('Asia/Shanghai'))
    elapsed_time = datetime_obj - unix_epoch
    return elapsed_time.total_seconds()


def to_human_readable_time(datetime_obj: datetime.datetime):
    return datetime_obj.isoformat()


@cachetools.func.ttl_cache(maxsize=1, ttl=60)
def retrieve_managebac_calendar(timeout=20):
    cal_text = requests.get(GET_ICAL_URL, timeout=timeout).text
    cal = icalendar.Calendar.from_ical(cal_text)
    return cal


def retrieve_baidu_copy_of_calendar():
    baidu_storage = BaiduCloudStorage()
    cal_text = baidu_storage.download_as_bytes(BAIDU_CALENDAR_FILE)
    if cal_text:
        cal = icalendar.Calendar.from_ical(cal_text)
    else:
        cal = icalendar.Calendar()
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


def retrieve_baidu_homework(date_str):
    baidu_storage = BaiduCloudStorage()
    homework_json_file = os.path.join(HOMEWORK_ROOT, date_str, 'homework.json')
    if not baidu_storage.file_exists(homework_json_file):
        return dict()

    homework_json = baidu_storage.download_as_bytes(homework_json_file)
    try:
        homework_dict = json.loads(homework_json)
    except json.decoder.JSONDecodeError:
        homework_dict = dict()

    return homework_dict


def extract_youtube_video_list_from_description(description: typing.Text):
    url_list = []
    for line in description.split('\n'):
        if 'youtube' in line and 'http' in line:
            url_list.append(line.strip())
    return url_list


def retrieve_homework_youtube_video_list_by_date(date_str: str, where: str):
    assert where in ['baidu', 'managebac']
    if where == 'baidu':
        homework_dict = retrieve_baidu_homework(date_str)
    elif where == 'managebac':
        cal = retrieve_managebac_calendar()
        event_dict = calendar_to_list_of_dicts(cal)
        homework_dict = event_dict.get(date_str, {})
    else:
        raise ValueError('Invalid where parameter. %s' % where)
    video_list = []
    for video_info in homework_dict:
        description = video_info.get('description', '')
        video_list += extract_youtube_video_list_from_description(description)
    return video_list


def retrieve_downloaded_youtube_video_list_by_date(date_str: str):
    baidu_storage = BaiduCloudStorage()
    video_json_file = os.path.join(HOMEWORK_ROOT, date_str, 'video.json')
    if not baidu_storage.file_exists(video_json_file):
        return dict()

    video_json = baidu_storage.download_as_bytes(video_json_file)
    video_dict = json.loads(video_json)
    #
    # video_dict structure:
    # [
    #   {
    #     'url': 'https://www.yutube.com/ABCDEFD'
    #     'filename': 'Video File Name.ABCDEF.mp4'
    #   },
    #   ....
    # ]
    #
    return video_dict


def get_videos_to_be_downloaded(date_str: str):
    downloaded_video_list = retrieve_downloaded_youtube_video_list_by_date(date_str)
    downloaded_video_set = {video['url'] for video in downloaded_video_list}
    homework_video_set = set(retrieve_homework_youtube_video_list_by_date(date_str, where="baidu"))
    return (homework_video_set - downloaded_video_set,
            downloaded_video_list)


def update_downloaded_video_list(video_list: list, date_str: str):
    video_list_json = json.dumps(video_list)
    baidu_storage = BaiduCloudStorage()
    remote_video_json_file = os.path.join(HOMEWORK_ROOT, date_str, 'video.json')
    baidu_storage.upload_bytes(video_list_json, remote_video_json_file)


def download_youtube_video(url: str, ydl_opts: dict = None) -> str:
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
        ydl.download(url)
    with open('info.json') as rfile:
        info_dict = json.load(rfile)
        filename = info_dict['_filename']
    assert os.path.isfile(filename), 'Download failed!'
    return filename


def download_and_upload_youtube_video(
        date_str: str,
        url: str,
        fake_download=False,
        fake_upload=False) -> dict:

    ydl_opts = {'simulate': True} if fake_download else None
    filename = download_youtube_video(url, ydl_opts)

    if not os.path.isfile(filename):
        raise FileNotFoundError(filename)

    if fake_upload:
        remote_filename = os.path.join(HOMEWORK_ROOT, date_str, os.path.basename(filename))
        baidu_storage = BaiduCloudStorage()
        baidu_storage.upload(filename, remote_filename)
        if not baidu_storage.file_exists(remote_filename):
            raise RuntimeError('upload %s failed!' % remote_filename)

    return {
        'url': url,
        'filename': filename,
    }


def set_timezone_to_shanghai():
    os.environ['TZ'] = 'Asia/Shanghai'


class BaiduCloudStorage(object):
    def __init__(self):
        self._bypy = bypy.ByPy()

    def upload(self, filename: str, remotepath: str = ''):
        if os.path.isfile(filename):
            self._bypy.upload(filename, remotepath)
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
            self._bypy.upload(local_file, remotepath)

    def download(self, filepath: str, localpath: str = ''):
        self._bypy.download(filepath, localpath)

    def download_as_bytes(self, filepath: str):
        if not self.file_exists(filepath):
            return b''

        with ScopedTempDir() as temp_dir:
            local_file = os.path.join(temp_dir, 'tempfile')
            self._bypy.download(filepath, local_file)
            with open(local_file, 'rb') as rfile:
                contents = rfile.read()
        return contents

    def file_exists(self, filepath):
        return self._bypy.meta(filepath) == 0

    def makedir(self, dir_name: str) -> None:
        if self.file_exists(dir_name):
            return
        else:
            res = self._bypy.mkdir(dir_name)
            assert res == 0


class LocalStorage(object):
    def __init__(self, rootdir='.'):
        self._rootdir = rootdir

    def _fullpath(self, path):
        return os.path.join(self._rootdir, path)

    def upload(self, filename: str, remotepath: str = ''):
        if remotepath.endswith('/') or remotepath == '':
            remotepath += os.path.basename(filename)

        if os.path.isfile(filename):
            shutil.copyfile(filename, self._fullpath(remotepath))
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
        return os.path.exists(filepath)

    def makedir(self, dir_name: str) -> None:
        try:
            os.makedirs(self._fullpath(dir_name))
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(self._fullpath(dir_name)):
                pass
            else:
                raise

BaiduCloudStorage = LocalStorage

class ScopedTempDir(object):
    def __init__(self, suffix='', parent_dir=None):
        self._suffix = suffix
        self._parent_dir = parent_dir
        self._dir = None
        self._entered = False

    def __enter__(self):
        self._dir = tempfile.mkdtemp(self._suffix, dir=self._parent_dir)
        atexit.register(self._ensure_tmp_dir_removed)
        return self._dir

    def __exit__(self, exc_type, exc_value, traceback):
        self._ensure_tmp_dir_removed()

    def _ensure_tmp_dir_removed(self):
        if self._dir:
            shutil.rmtree(self._dir)
            self._dir = None

    def take(self):
        if self._entered:
            raise Exception('Wrong usage!')
        self._entered = True
        return self.__enter__()

    def release(self):
        if not self._entered:
            raise Exception('Wrong usage!')
        self._entered = False
        self.__exit__(None, None, None)
