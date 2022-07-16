# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

SITESUBTITLE = "On reverse engineering, programming, and maybe some other stuff."

OUTPUT_PATH = 'static/'

# If your site is available via HTTPS, make sure SITEURL begins with https://
SITEURL = 'https://alschwalm.com/blog/static'
RELATIVE_URLS = True

FEED_ALL_ATOM = 'rss/index.xml'

DELETE_OUTPUT_DIRECTORY = True

# Following items are often useful when publishing

#DISQUS_SITENAME = ""
#GOOGLE_ANALYTICS = ""

HOME_COVER = './images/2016/12/header-background.jpg'

ARTICLE_URL = '{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = '{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'

SOCIAL = (('twitter', 'https://twitter.com/alschwalm'),
          ('rss', 'https://alschwalm.com/blog/static/rss/'))
