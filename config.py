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
SQLALCHEMY_ECHO=True

SUPPORTED_LANGUAGES = {'de': 'Deutsch', 'en': 'English', 'fr': 'Francais'}
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_TIMEZONE = 'UTC'

DEFAULT_CURRENCY_ID = 101
