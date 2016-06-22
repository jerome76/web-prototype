Build the android / iOS client with the following command:

buildozer android debug deploy run logcat

# IMPORTANT: remove termios from .buildozer/android/platform/python-for-android/src/blacklist.txt
# IMPORTANT: remove termios from .buildozer/android/platform/python-for-android/dist/blacklist.txt


Build the Windows POS client with the following command.

python -m PyInstaller pos.spec
