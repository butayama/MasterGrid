[app]
title = MasterGrid
package.name = MasterGrid
package.domain = org.mastergrid
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = kivy,pyjnius
icon.filename = %(source.dir)s/data/icon.png
orientation = all
fullscreen = 1
android.api = 24
android.minapi = 23
android.ndk = 13b
android.ndk_path = ~/Android/android-ndk-r13b
android.sdk_path = ~/Android/SDK
android.arch = arm64-v8a
android.add_src = src/org

[buildozer]
log_level = 2
warn_on_root = 1
