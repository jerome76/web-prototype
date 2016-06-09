#!/bin/bash
cd /home/pi/dev/erp_client/
/usr/bin/python manage.py runserver --port=8081 -h 0.0.0.0 >>/var/log/sl/erp-client.log 2>&1

