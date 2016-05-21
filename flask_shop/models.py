from flask_shop import app


class Product(app.db.Model):
    __tablename__ = 'product_product'
    id = app.db.Column(app.db.Integer, primary_key=True)
    code = app.db.Column(app.db.String(64), unique=False)
    description = app.db.Column(app.db.String(64), unique=False)
    template = app.db.Column(app.db.Integer, app.db.ForeignKey("product_template.id"))
    template_ref = app.db.relationship("Template")
    attributes = app.db.Column(app.db.Text, unique=False)

class Customer(app.db.Model):
    __tablename__ = 'party_address'
    id = app.db.Column(app.db.Integer, primary_key=True)
    party = app.db.Column(app.db.Integer, unique=False)
    city = app.db.Column(app.db.String(64), unique=False)
    name = app.db.Column(app.db.String(64), unique=False)
    country = app.db.Column(app.db.Integer, unique=False)
    subdivision = app.db.Column(app.db.Integer, unique=False)
    zip = app.db.Column(app.db.String(64), unique=False)
    streetbis = app.db.Column(app.db.String(64), unique=False)
    street = app.db.Column(app.db.String(64), unique=False)
    active = app.db.Column(app.db.Boolean, unique=False)
    delivery = app.db.Column(app.db.Boolean, unique=False)
    invoice = app.db.Column(app.db.Boolean, unique=False)


class Template(app.db.Model):
    __tablename__ = 'product_template'
    id = app.db.Column(app.db.Integer, primary_key=True)
    name = app.db.Column(app.db.String(64))
    sale_uom = app.db.Column(app.db.Integer)


class Property(app.db.Model):
    __tablename__ = 'ir_property'
    id = app.db.Column(app.db.Integer, primary_key=True)
    res = app.db.Column(app.db.String(64))
    field = app.db.Column(app.db.Integer)
    value = app.db.Column(app.db.String(64))


class User():
    id = None
    nickname = None
    email = None
    posts = None

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)  # python 2
        except NameError:
            return str(self.id)  # python 3

    def __repr__(self):
        return '<User %r>' % (self.nickname)