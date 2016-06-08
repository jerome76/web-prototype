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
    DEBUG=app.config['MAIL_SERVER_DEBUG'],
    # EMAIL SETTINGS
    MAIL_SERVER=app.config['MAIL_SERVER'],
    MAIL_PORT=app.config['MAIL_PORT'],
    MAIL_USE_SSL=app.config['MAIL_USE_SSL'],
    MAIL_USERNAME=app.config['MAIL_USERNAME'],
    MAIL_PASSWORD=app.config['MAIL_PASSWORD']
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