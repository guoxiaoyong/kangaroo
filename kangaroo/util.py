# Author: Xiaoyong Guo

import atexit
import datetime
import os
import shutil
import tempfile
import typing

import bypy
import icalendar
import requests
import pytz


MANAGEBAC_ICAL_URL = \
    "webcal://fudan.managebac.com/parent/events/child/11748276/token/4fbc3f50-5564-0134-a2c7-0cc47aa8e996.ics"

GET_ICAL_URL = MANAGEBAC_ICAL_URL.replace("webcal", "http")

HOMEWORK_ROOT = 'fdis/homework/kangaroo'


def to_timestamp(datetime_obj: datetime.datetime):
    # Well, not really Unix epoch.
    unix_epoch = datetime.datetime(1970, 1, 1, tzinfo=pytz.timezone('Asia/Shanghai'))
    elapsed_time = datetime_obj - unix_epoch
    return elapsed_time.total_seconds()


def to_human_readable_time(datetime_obj: datetime.datetime):
    return datetime_obj.isoformat()


def retrieve_managebac_calendar(timeout=20):
    cal_text = requests.get(GET_ICAL_URL, timeout=timeout).text
    cal = icalendar.Calendar.from_ical(cal_text)
    return cal


def retrieve_baidu_copy_of_calendar():
    cal_file = os.path.join(HOMEWORK_ROOT, 'calendar.ics')
    baidu_storage = BaiduCloudStorage()
    cal_text = baidu_storage.download_as_bytes(cal_file)
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


def extract_youtube_from_description(description: typing.Text):
    url_list = []
    for line in description.split('\n'):
        if 'youtube' in line and 'http' in line:
            url_list.append(line.strip())
    return url_list


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
