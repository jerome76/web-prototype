Build the android / iOS client with the following command:

buildozer android debug deploy run logcat

# IMPORTANT: remove termios from .buildozer/android/platform/python-for-android/src/blacklist.txt
# IMPORTANT: remove termios from .buildozer/android/platform/python-for-android/dist/blacklist.txt


Build the Windows POS client with the following command.

python -m PyInstaller pos.spec


Windows:
python -m pip install --upgrade pip wheel setuptools
python -m pip install docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew
python -m pip install kivy.deps.gstreamer --extra-index-url https://kivy.org/downloads/packages/simple/
python -m pip install kivy



