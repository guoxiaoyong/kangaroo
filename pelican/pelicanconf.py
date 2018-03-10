#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Guo Xiaoyong'
SITENAME = 'FDIS G2 Kangaroo Homework'
SITEURL = ''  # dev environment, will be overriden by publishconf.py
THEME = 'themes/bricks'

PATH = 'content'

TIMEZONE = 'Asia/Shanghai'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

STATIC_PATHS = {'images', 'extra/favicon.ico'}
EXTRA_PATH_METADATA = {
    'extra/favicon.ico': {'path': 'favicon.ico'}
}

# Blogroll
LINKS = (
    ('Video Link', 'https://pan.baidu.com/s/1DnNp9VrFSWz3B_ZGNQA9zg'),
    ('ManageBac', 'https://fudan.managebac.com/'),
    ('FDIS', 'http://www.fdis.net.cn/'),
)

# Social widget
SOCIAL = (('github', 'http://www.github.com/guoxiaoyong'),
          ('twitter', 'http://twitter.com'),)

DEFAULT_PAGINATION = False

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True
