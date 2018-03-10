# Author: Guo Xiaoyong
# Date: 2018-03-09

import glob
import json
import os

import dateutil.parser

import util


def process_http(line):
    words = line.split()
    url_list = []
    for word in words:
        if word.startswith('http://') or word.startswith('https://'):
            url_list.append(word)

    for url in url_list:
        new_word = '[%s](%s)' % (url, url)
        line = line.replace(url, new_word)
    return line


def process_desc(text):
    lines = text.split('\n')
    lines = [process_http(line) for line in lines]
    return '\n\n'.join(lines)


def generate_blog_content(date_str: str):
    homework_json_file = util.get_homework_json_filepath(date_str)
    dt = dateutil.parser.parse(date_str)
    with open(homework_json_file, 'r') as rfile:
        event_list = json.load(rfile)
    content = ['Title: %s Homework\nDate: %s\n\n' % (date_str, dt)]
    for event in event_list:
        if 'ES Menu' in event['summary']:
            continue
        desc = process_desc(event['description'])
        content.append('## %s\n\n%s\n' % (event['summary'], desc))
    return '\n'.join(content)


def main():
    dir_list = glob.glob(os.path.join(util.HOMEWORK_ROOT, '*'))
    for fullpath in dir_list:
        if os.path.isfile(fullpath):
            continue
        date_str = os.path.basename(fullpath)
        text = generate_blog_content(date_str)
        filename = os.path.join(
            util.get_repo_path(), 'pelican', 'content',
            'blog', '%s.md' % date_str)
        with open(filename, 'w') as wfile:
            wfile.write(text)


if __name__ == '__main__':
    main()
