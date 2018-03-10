# Author: Guo Xiaoyong
# Date: 2018-03-10

import os

import util


def get_css_filepath():
    return os.path.join(util.get_repo_path(), 'pelican', 'output', 'theme', 'css', 'lamboz.css')


def patch_css():
    filepath = get_css_filepath()
    with open(filepath, 'r') as rfile:
        lines = rfile.readlines()
    for num, line in enumerate(lines):
        if '/theme/img/' in line:
            lines[num] = line.replace('/theme', '/kangaroo/theme')
    with open(filepath, 'w') as wfile:
        wfile.writelines(lines)


if __name__ == '__main__':
    patch_css()
