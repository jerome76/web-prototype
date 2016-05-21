#!/usr/bin/python2.7
#
# Small script to show PostgreSQL and Pyscopg together
#

import psycopg2

try:
    conn = psycopg2.connect("dbname='tryton_dev' user='tryton' host='localhost' password='password'")
    print "Connection was successful"
except:
    print "I am unable to connect to the database"
