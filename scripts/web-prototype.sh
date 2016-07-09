#!/bin/bash
cd /home/pi/dev/web-prototype/
#/usr/bin/python run.py >>/var/log/sl/web-prototype.log 2>&1
/usr/local/bin/gunicorn --bind 0.0.0.0:5000 flask_shop:app >>/var/log/sl/web-prototype.log 2>&1
