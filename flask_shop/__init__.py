from flask import Flask, g
from flask_login import LoginManager
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask.json import JSONEncoder
from flask_mail import Mail

app = Flask(__name__)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.db = SQLAlchemy(app)
app.mail = Mail(app)
app.config.update(
    DEBUG=True,
    # EMAIL SETTINGS
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME = 'milliondog.com@gmail.com',
    MAIL_PASSWORD = 'milliondog.123'
    )
mail = Mail(app)

babel = Babel(app)
lm = LoginManager()
lm.init_app(app)
from flask_shop import views
from flask_shop import models
from flask_shop import server

class CustomJSONEncoder(JSONEncoder):
    """This class adds support for lazy translation texts to Flask's
    JSON encoder. This is necessary when flashing translated texts."""
    def default(self, obj):
        from speaklater import is_lazy_string
        if is_lazy_string(obj):
            try:
                return unicode(obj)  # python 2
            except NameError:
                return str(obj)  # python 3
        return super(CustomJSONEncoder, self).default(obj)

app.json_encoder = CustomJSONEncoder