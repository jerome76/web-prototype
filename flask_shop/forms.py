from flask_wtf import Form
from wtforms import StringField, BooleanField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, EqualTo, AnyOf


class LoginForm(Form):
    email = StringField('email', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('remember_me', default=False)


class RegisterForm(Form):
    username = StringField('username', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    password = PasswordField('password', validators=[EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('confirm', validators=[DataRequired()])


class CheckoutForm(Form):
    name = StringField('name', validators=[DataRequired()])
    street = StringField('street', validators=[DataRequired()])
    street2 = StringField('street2')
    zip = StringField('zip', validators=[DataRequired()])
    city = StringField('city', validators=[DataRequired()])
    state = SelectField('State')
    country = SelectField('Country', validators=[DataRequired()])
    # state = StringField('state')
    # country = StringField('country', validators=[DataRequired()])
    delivery = BooleanField('delivery', default=False)
    invoice = BooleanField('invoice', default=False)
    acceptterms = BooleanField('acceptterms', default=False,
                               validators=[AnyOf([True], message='You must accept the terms and conditions')])


class ContactForm(Form):
    name = StringField('name', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired()])
    subject = StringField('subject', validators=[DataRequired()])
    message = TextAreaField('message', validators=[DataRequired()])
    answer = StringField('answer', validators=[DataRequired()])
