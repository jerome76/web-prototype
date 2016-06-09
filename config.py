# -*- coding: utf-8 -*-
# ...
# available languages
LANGUAGES = {
    'en': 'English',
    'de': 'Deutsch'
}

WTF_CSRF_ENABLED = True
SECRET_KEY = '489209348024859h2kjhfdij'
SQLALCHEMY_DATABASE_URI = "postgresql://tryton:password@localhost:5432/tryton_dev"
SQLALCHEMY_ECHO = True
TRYTON_DATABASE_NAME = "tryton_dev"
TRYTON_CONFIG_FILE = "./tryton.conf"
FLASK_LOG_DIRECTORY = "/var/log/sl/"
FLASK_LOG_FILE = "web-prototype.log"

SUPPORTED_LANGUAGES = {'de': 'Deutsch', 'en': 'English', 'fr': 'Francais'}
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'

PAYPAL_SHOP_DOMAIN = 'http://milliondog.ddns.net'
PAYPAL_BUSINESS = 'express3.com-facilitator@gmail.com'

CONTACT_FORM_EMAIL_SEND_ADDRESS = 'milliondog.com@gmail.com'
# EMAIL SETTINGS
MAIL_SERVER_DEBUG = True
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'milliondog.com@gmail.com'
MAIL_PASSWORD = 'password'

UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = set(['csv'])
# Max content length for file upload: 1 MB
MAX_CONTENT_LENGTH = 1 * 1024 * 1024

DEFAULT_CURRENCY_ID = 101
DEFAULT_ADMIN_USERNAME = 'user@host.com'
DEACTIVATE_PRODUCT_WHEN_SOLD = True
