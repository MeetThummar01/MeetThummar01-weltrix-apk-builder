[app]
title = Weltrix Video Downloader
package.name = weltrixdownloader
package.domain = com.weltrix
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,yt-dlp,requests,pillow,pyjnius,setuptools,cython,certifi
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
android.ndk = 25b
android.minapi = 23
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
