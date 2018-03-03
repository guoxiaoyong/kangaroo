# Author: Xiaoyong Guo

import youtube_dl

def download_video(url):
  with youtube_dl.YoutubeDL() as ydl:
    ydl.download(url)
