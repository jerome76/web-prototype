# -*- coding: utf-8 -*-
from flask import Flask, render_template, flash, redirect, session, url_for, request, g, send_from_directory
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from flask_shop import app
from .forms import LoginForm, RegisterForm, ContactForm, CheckoutForm
from proteus import config, Model, Wizard, Report
from flask_babel import gettext, refresh
from flask_mail import Message
from flask_shop import babel, models
from werkzeug.datastructures import ImmutableOrderedMultiDict
import time
import requests
import json
import os
from decimal import *
import psycopg2
import urlparse
from datetime import timedelta
from passlib.hash import pbkdf2_sha256
from validate_email import validate_email
from loader import csvimport
import zipfile

CONFIG = app.config['TRYTON_CONFIG_FILE']
DATABASE_NAME = app.config['TRYTON_DATABASE_NAME']
config.set_trytond(DATABASE_NAME, config_file=CONFIG)


def format_currency_amount(amount):
    return '{:20,.2f}'.format(amount)


def getShipping(product_name):
    Product = Model.get('product.product')
    product = Product.find(['name', '=', product_name])
    if product is not None:
        return product[0]


def getProductDirect(category=None, size=None, available_only=None):
    if category is None:
        category_condition = 'and 1 = 1 '
    else:
        category_condition = "and pc.name like '%" + category + "%' "
    if size is None:
        size_condition = 'and 1 = 1 '
    else:
        size_condition = "and product.attributes like '%" + size + "%' "
    if available_only is None:
        available_only_condition = 'and 1 = 1 '
    elif available_only:
        available_only_condition = "and product.attributes like '%\"available\": true,%' "
    else:
        available_only_condition = 'and 1 = 1 '
    con = None
    result = None
    try:
        result = urlparse.urlparse(app.config['SQLALCHEMY_DATABASE_URI'])
        con = psycopg2.connect(database=result.path[1:], host=result.hostname, user=result.username,
                               password=result.password)
        cur = con.cursor()
        cur.execute("SELECT product.id, product.code, product.description, " +
                    "t.name, product.template, product.attributes, " +
                    "uom.id as uom_id, uom.name as uom_name, uom.symbol as uom_symbol, uom.rounding as uom_rounding, "
                    "trim(p.value, ',') as list_price, " +
                    "pc.name as category " +
                    "from product_product product, " +
                    "product_template t, ir_property p, product_uom uom, " +
                    '"product_template-product_category" ptpc, product_category pc ' +
                    "where product.code <> '' " +
                    "and product.template = t.id "
                    "and t.sale_uom = uom.id " +
                    "and p.res = 'product.template,'||t.id " +
                    "and p.field = (select f.id from ir_model_field f, ir_model m "
                    "       where m.model = 'product.template' and m.id = f.model and f.name = 'list_price') " +
                    "and t.id = ptpc.template " +
                    category_condition +
                    size_condition +
                    available_only_condition +
                    "and ptpc.category = pc.id " +
                    "order by product.id")

        resultset = cur.fetchall()
        result = []
        for p in resultset:
            row = dict([])
            row['id'] = p[0]
            row['code'] = p[1]
            row['description'] = p[2]
            row['name'] = p[3]
            row['template'] = p[4]
            if p[5] is not None:
                json_acceptable_string = p[5].replace("'", "\"")
                row['attributes'] = json.loads(json_acceptable_string)
            row['uom_id'] = p[6]
            row['uom_name'] = p[7]
            row['uom_symbol'] = p[8]
            row['uom_rounding'] = p[9]
            row['list_price'] = format_currency_amount(Decimal(p[10]) * Decimal(session['currency_rate']))
            row['category'] = p[11]
            result.append(row)
        print result
    except psycopg2.DatabaseError, e:
        print 'Error %s' % e
    finally:
        if con:
            con.close()
    return result


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_title=gettext(u'Page not found'),
                           error_message=gettext(u'The page you are trying to access does not exist.')), 404


@app.errorhandler(500)
def page_not_found(e):
    return render_template('error.html', error_title=gettext(u'Internal server error'),
                           error_message=gettext(u'Something went wrong.')), 500


@app.errorhandler(403)
def page_not_found(e):
    return render_template('error.html', error_title=gettext(u'Access forbidden'),
                           error_message=gettext(u'You are not allowed to access this page.')), 403


@babel.localeselector
def get_locale():
    try:
        if session['lang_code'] is not None:
            return session['lang_code']
    except KeyError:
        # session is not initialized
        return 'de'
    return app.config['BABEL_DEFAULT_LOCALE']

@babel.timezoneselector
def get_timezone():
    user = g.get('user', None)
    if user is not None:
        return user.timezone

@app.before_request
def make_session_permanent():
    session.permanent = False
    app.permanent_session_lifetime = timedelta(minutes=5)

@app.before_request
def before_request():
    g.user = current_user
    g.user.locale = get_locale()
    try:
        if session['lang_code'] is None:
            session['lang_code'] = 'de'
        if session['currency_code'] is None:
            session['currency_code'] = 'CHF'
        if session['currency_rate'] is None:
            session['currency_rate'] = 1.00
        if session['logged_in'] is None:
            session['logged_in'] = False
    except KeyError:
        # session not initialized
        session['lang_code'] = 'de'
        session['currency_code'] = 'CHF'
        session['currency_rate'] = 1.00
        session['logged_in'] = False


def getProductFromSession():
    try:
        cart = session['cart']
        products = []
        for p in cart:
            Product = Model.get('product.product')
            product = Product.find(['id', '=', p])
            if product is not None:
                product[0].list_price = Decimal(format_currency_amount(product[0].list_price * Decimal(session['currency_rate'])))
                products.append(product[0])
        return products
    except KeyError:
        print("cart is empty.")
        return None


@app.route("/about/")
def about():
    page_topic = gettext(u'About us')
    page_content = gettext(u'''<h4><p>We created Milliondog because we love dogs. Milliondog symbolizes the importance of a dog for his owner and our philosophy reflects just that. Each Milliondog Cosy is unique in material and colour and emphasises the individual personality and uniqueness of your pawesome darling.</p>
        <p>We love our work and you can see this in every Cosy.</p>
        </h4>''')
    return render_template('about.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('About us'))

@app.route("/sendus/")
def sendus():
    page_topic = gettext(u'Send us')
    page_content = gettext(u'''<h4><p>We welcome your enquiries regarding our exclusive service using your own fabrics, for example we can use material from your children’s, parent’s or partner’s clothes to make a special Milliondog-Cosy for your dog. Get in touch with us so we can work together to give your dog a unique look.</p>
        <p>Let your dog play his own part by wearing a Milliondog-Cosy at a special day in your life.</p>
        <p>For more information contact us by <a href=\"mailto:informme@milliondog.com\">Email</a>.</p>
        </h4>''')
    return render_template('sendus.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Send us'))

@app.route("/product/<productid>")
def product(productid=None):
    try:
        if session['currency_rate'] is None:
            session['currency_rate'] = 1.000
    except KeyError:
        session['currency_rate'] = 1.000

    page_topic = gettext(u'Product')
    page_content = gettext(u'Product:')
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Product = Model.get('product.product')
    product = Product.find(['id', '=', productid])
    item = {}
    if len(product) > 0:
        item['id'] = product[0].id
        item['code'] = product[0].code
        item['image'] = product[0].attributes['image']
        item['size'] = product[0].attributes['size']
        item['name'] = product[0].name
        item['description'] = product[0].description
        item['list_price'] = '{:20,.2f}'.format(Decimal(product[0].list_price) * Decimal(session['currency_rate']))
    return render_template('product.html', pt=page_topic, pc=page_content, product=item,
                           title="Milliondog", page=gettext('Product'))


@app.route("/custom-made")
def custommade():
    page_topic = gettext(u'Shop')
    page_content = gettext(u'<h4><p>You do not find the appropriate Cosy in the shop? We would love to advise you for your individual material combination.</p></h4>') + \
                   gettext(u'''<h4><p>We welcome your enquiries regarding our exclusive service using your own fabrics, for example we can use material from your children’s, parent’s or partner’s clothes to make a special Milliondog-Cosy for your dog. Get in touch with us so we can work together to give your dog a unique look.</p>
        <p>Let your dog play his own part by wearing a Milliondog-Cosy at a special day in your life.</p>
        <p>For more information contact us by <a href=\"mailto:informme@milliondog.com\">Email</a>.</p>
        </h4>''')
    category = gettext(u'Custom-made')
    resp = render_template('custom-made.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Shop'),
                           category=category)
    return resp


@app.route("/categories")
def category():
    return render_template('categories.html')


@app.route("/shop/<category>/<size>")
@app.route("/shop/<category>")
@app.route("/shop/")
def shop(category=None, size=None):
    try:
        if session['currency_rate'] is None:
            session['currency_rate'] = 1.000
    except KeyError:
        session['currency_rate'] = 1.000

    print("Shop ")
    page_topic = gettext(u'Shop')
    page_content = gettext(u'''<h4><p>Every Milliondog-Cosy is a handmade unique piece and emphasises the personality of your dog.
        <br>The individual, careful processing of the comfortable cotton and jersey materials for a Milliondog-Cosy
        begins for us with the choice of the special materials and their combination with each other.
        <br>Give your dog the friendly look he deserves – every dog can be a true Milliondog.
        <br>You can choose a standard Cosy sizes or you can order a Cosy in exactly the right size for your dog.
        <br>Each Cosy is reversible, it can be worn on either side.</p>
        </h4>''')
    start = time.time()
    # fastproducts = models.Product.query.all()
    directproducts = getProductDirect(category, size, available_only=True)
    end = time.time()
    print("Shop.getProductDirect " + str(end - start) + " ms.")
    resp = render_template('shop.html', pt=page_topic, pc=page_content, db_model='Products', db_list=directproducts,
                           title="Milliondog", page=gettext('Shop'), category=category)
    return resp

@app.route("/gallery/")
def gallery():
    page_topic = gettext(u'Gallery')
    page_content = gettext(u'Gallery:')
    return render_template('gallery.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Gallery'))

@app.route("/products/")
def products():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Product = Model.get('product.product')
    product = Product.find(['id', '>=', '0'])
    Attachments = Model.get('ir.attachment')
    Template = Model.get('product.template')
    attachmentlist = []
    for n in product:
        template = Template.find(['id', '=', n.id])
        for a in template:
            attachmentlist.extend(Attachments.find(['resource', '=', 'product.template,'+str(a.id)]))
    return render_template('products.html', db_model='Products', db_list=product, attachments=attachmentlist, title="Milliondog", page=gettext('Products'))

@app.route("/")
@app.route('/index/')
def index():
    try:
        if session['lang_code'] is None:
            session['lang_code'] = 'de'
        if session['currency_code'] is None:
            session['currency_code'] = 'CHF'
    except KeyError:
        # session not initialized
        session['lang_code'] = 'de'
        session['currency_code'] = 'CHF'
    page_topic = gettext(u'Start')
    page_content = gettext(u'exclusive accessoires for your awesome darling')
    return render_template('index.html', pt=page_topic, pc=page_content, title="Milliondog", page='the cosy-company')


@app.route('/productcategories/')
def product_categories():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    ProductCategory = Model.get('product.category')
    categories = ProductCategory.find(['id', '>=', '0'])
    idlist = [c.name for c in categories]
    return render_template('productcategories.html', db_model='Product Categories', db_list=idlist,
                           title="Milliondog", page='Product Categories')


@app.route('/cart/')
def cart():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    User = Model.get('res.user')
    user = User.find(['id', '=', '1'])
    cart = getProductFromSession()
    sub_total_tmp = Decimal(0.00)
    if cart:
        for p in cart:
            sub_total_tmp += p.list_price
    shipping = getShipping('Shipping local')
    shipping_cost_temp = 0.00
    if shipping is not None:
        if sub_total_tmp < Decimal(150.00*session['currency_rate']):
            shipping_cost_temp = shipping.list_price * Decimal(session['currency_rate'])
            sub_total_tmp += shipping_cost_temp

    sub_total = format_currency_amount(sub_total_tmp)
    shipping_cost = format_currency_amount(shipping_cost_temp)
    session['user_name'] = 'paypal_testuser'
    return render_template('cart.html', message=user[0].name, id=user[0].id, cart=cart, sub_total=sub_total,
                           shipping=shipping, shipping_cost=shipping_cost, shipping_text=gettext(u'Shipping local'),
                           title="Milliondog", page='Cart')


@app.route('/cart/add/<productid>')
def cart_add(productid=None):
    cart = []
    cart_item_count = 0
    try:
        cart = session['cart']
        cart_item_count = session['cart_item_count']
    except KeyError:
        session['cart'] = cart
        session['cart_item_count'] = cart_item_count
    if productid not in cart:
        cart.append(productid)
        session['cart_item_count'] = cart_item_count + 1
    return redirect("/cart")


@app.route('/cart/remove/<productid>')
def cart_remove(productid=None):
    try:
        cart = session['cart']
        cart_item_count = session['cart_item_count']
        if productid in cart:
            cart.remove(productid)
            session['cart_item_count'] = cart_item_count - 1
    except KeyError:
        print('view.py.cart_remove-KeyError: ' + productid)

    return redirect("/cart")


@app.route('/account/')
def account():
    try:
        userid = session['userid']
    except KeyError:
        return redirect("/login")

    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    User = Model.get('res.user')
    user = User.find(['id', '=', userid])
    Sale = Model.get('sale.sale')
    party = user[0].name.split(",")    # user.name = 'party,3'
    salelist = Sale.find(['party', '=', int(party[1])])
    return render_template('account.html', message=user[0].name,
                           id=user[0].id, sale_list=salelist, title="Milliondog", page='Account')

@app.route('/admin/')
@app.route('/admin/<section>')
def admin(section='user'):
    if not session['logged_in']:
        return redirect('/login')
    if session['user_name'] != app.config['DEFAULT_ADMIN_USERNAME']:
        return redirect('/login')
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    username = ''
    userid = 0
    partylist = None
    stocklist = None
    productlist = None
    salelist = None
    invoicelist = None
    if section == 'user':
        User = Model.get('res.user')
        user = User.find(['id', '=', '1'])
        if len(user) > 0:
            username = user[0].name
            userid = user[0].id
    elif section == 'party':
        Party = Model.get('party.party')
        partylist = Party.find(['id', '>=', '0'])
    elif section == 'stock':
        Stock = Model.get('stock.move')
        stocklist = Stock.find(['id', '>=', '0'])
    elif section == 'product':
        Product = Model.get('product.product')
        productlist = Product.find(['id', '>=', '0'])
    elif section == 'sale':
        Sale = Model.get('sale.sale')
        salelist = Sale.find(['id', '>=', '0'])
    elif section == 'invoice':
        Invoice = Model.get('account.invoice')
        invoicelist = Invoice.find(['id', '>=', '0'])
    return render_template('admin.html', message=username,
                           id=userid, db_list=partylist, invoice_list=invoicelist, sale_list=salelist,
                           stock_list=stocklist, product_list=productlist, title="Milliondog", page='Account')


@app.route('/logfile/')
def show_log():
    if not session['logged_in']:
        return redirect('/login')
    return send_from_directory(app.config['FLASK_LOG_DIRECTORY'], app.config['FLASK_LOG_FILE'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    page_topic = 'File ' + filename + ' uploaded successfully.'
    if not session['logged_in']:
        return redirect('/login')
    # send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    return render_template('uploads.html',
                    title="Milliondog", page=gettext('Upload new File'), pt=page_topic)


@app.route('/upload/', methods=['GET', 'POST'])
def upload():
    page_topic = "Upload new File:"
    if not session['logged_in']:
        return redirect('/login')
    if not session['email'] == app.config['DEFAULT_ADMIN_USERNAME']:
        return redirect('/login')
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash(gettext(u'No file part'), 'danger')
            return redirect(request.url)
        file = request.files['file']
        file_type = request.form['file_type']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash(gettext(u'No file selected'), 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            if file_type == 'products':
                csvimport.import_products(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif file_type == 'product_categories':
                csvimport.import_product_categories(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif file_type == 'product_attributeset':
                csvimport.import_product_attributeset(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif file_type == 'product_template':
                csvimport.import_product_template(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif file_type == 'customers':
                csvimport.import_customers(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            elif file_type == 'import_supplier_shipments':
                try:
                    csvimport.import_shipment_in(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except ValueError as error:
                    flash(gettext(u'Could not process file: ') + repr(error), 'danger')
            elif file_type == 'webshop_images_zip':
                fh = open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb')
                z = zipfile.ZipFile(fh)
                for name in z.namelist():
                    outpath = app.config['WEBSHOP_PRODUCT_IMAGES_DIRECTORY']
                    if name[-4:].lower() == '.png' or name[-4:].lower() == '.jpg' or name[-5:].lower() == '.jpeg':
                        z.extract(name, outpath)
                fh.close()
            elif file_type == 'pos_images_zip':
                fh = open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb')
                z = zipfile.ZipFile(fh)
                for name in z.namelist():
                    outpath = app.config['POS_PRODUCT_IMAGES_DIRECTORY']
                    if name[-4:].lower() == '.png' or name[-4:].lower() == '.jpg' or name[-5:].lower() == '.jpeg':
                        z.extract(name, outpath)
                fh.close()
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    max_content_length_mb = app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024
    return render_template('upload.html',
                           title="Milliondog", page=gettext('Upload new File'), pt=page_topic,
                           max_content_length_mb=max_content_length_mb)


@app.route('/setlang/<language>')
@app.route('/setlang/<language>/<path:goto>')
def setlang(language=None, goto=None):
    setattr(g, 'lang_code', language)
    session['lang_code'] = language
    refresh()
    return redirect("/" + goto)

@app.route('/setcurrency/<currency>')
@app.route('/setcurrency/<currency>/<path:goto>')
def setcurrency(currency=None, goto=None):
    setattr(g, 'currency_code', currency)
    session['currency_code'] = currency
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    CurrencyRate = Model.get('currency.currency.rate')
    currency_rate = CurrencyRate.find(['id', '>', 0])
    for n in currency_rate:
        if n.currency.code == currency:
            session['currency_rate'] = float(n.rate)
    return redirect("/" + goto)

@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        is_valid = validate_email(form.email.data)
        if is_valid:
            config.set_trytond(DATABASE_NAME, config_file=CONFIG)
            User = Model.get('res.user')
            user = User.find(['login', '=', form.email.data])
            if user:
                passwordhash = user[0].password_hash
                print('User found: ' + user[0].login)
                start = time.time()
                is_valid = pbkdf2_sha256.verify(form.password.data, passwordhash)
                end = time.time()
                if is_valid:
                    flash(gettext(u'login successful.'), 'success')
                    print('login successful in ' + str(end-start) + ' msec.')
                    session['email'] = user[0].email
                    session['userid'] = user[0].id
                    session['partyid'] = user[0].name.split(",")[1]
                    session['logged_in'] = True
                    try:
                        if session['cart']:
                            return redirect('/checkout')
                    except KeyError:
                        return redirect('/cart')
                else:
                    flash(gettext(u'invalid email or password.'), 'danger')
                    print('login failed: invalid password')
            else:
                flash(gettext(u'invalid email or password.'), 'danger')
                print('No user found with login ' + form.email.data)
        else:
            flash(gettext(u'Invalid email address given.'), 'danger')
            print('login failed: invalid email')
    return render_template('login.html', title="Milliondog", page=gettext('Sign in'), form=form)

@app.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        is_valid = validate_email(form.email.data)
        if is_valid:
            config.set_trytond(DATABASE_NAME, config_file=CONFIG)
            User = Model.get('res.user')
            user = User.find(['email', '=', form.email.data])
            if user:
                flash(gettext(u'Email address already registered.'), 'danger')
                print('Email address ' + form.email.data + ' already registered.')
            else:
                config.set_trytond(DATABASE_NAME, config_file=CONFIG)
                print('Login requested for email="%s", username=%s' %
                      (form.email.data, str(form.username.data)))
                User = Model.get('res.user')
                user = User()
                if user.id < 0:
                    session['email'] = form.email.data
                    passwordhash = pbkdf2_sha256.encrypt(form.password.data, rounds=100000, salt_size=64)
                    user.login = form.email.data
                    user.password_hash = passwordhash
                    user.email = form.email.data
                    Party = Model.get('party.party')
                    party = Party()
                    party.name = form.username.data
                    Lang = Model.get('ir.lang')
                    (en,) = Lang.find([('code', '=', 'en_US')])
                    party.lang = en
                    party.save()
                    user.name = 'party,' + str(party.id)
                    user.save()
                    print('Registration successful for email="%s", username=%s' %
                          (form.email.data, form.username))
                    session['email'] = user.email
                    session['partyid'] = party.id
                    session['userid'] = user.id
                    session['logged_in'] = True
                    try:
                        if session['cart_item_count'] > 0:
                            flash(gettext(u'Registration successful. Please continue the checkout process.'), 'success')
                            return redirect('/checkout')
                    except:
                        session['cart_item_count'] = 0
                        flash(gettext(u'Registration successful.'), 'success')
                        return redirect('/shop')
                else:
                    flash(gettext(u'System is down.'), 'danger')
                    print('Cannot register email ' + form.email.data)
        else:
            flash(gettext(u'Invalid email address given.'), 'danger')
            print('Invalid email address ' + form.email.data)
    return render_template('register.html',
                           title="Milliondog", page=gettext('Register'), form=form)


@app.route('/logout/')
def logout():
    session.clear()
    return redirect('/')

@app.route('/contact/', methods=['GET', 'POST'])
def contact():
    page_topic = gettext(u'Contact')
    page_content = gettext(u'You can send us a message here:')
    form = ContactForm()
    if form.validate_on_submit():
        flash(gettext(u'Thank you for your message.'), 'success')
        send_to_email = app.config['CONTACT_FORM_EMAIL_SEND_ADDRESS']
        msg = Message("Neue Nachricht über milliondog.com Kontaktformular",
                  sender=send_to_email,
                  recipients=[send_to_email])
        msg.body = ('Name: %s\nEmail: %s\nBetreff: %s\n Nachricht: %s\n' %
                    (form.name.data, form.email.data, form.subject.data, form.message.data))
        msg.html = ('<b>Formularfelder</b><br>Name: %s<br>Email: %s<br>Betreff: %s<br> Nachricht: %s<br>' %
                    (form.name.data, form.email.data, form.subject.data, form.message.data))
        app.mail.send(msg)
    return render_template('contact.html',
                           pt=page_topic, pc=page_content, title="Milliondog", page=gettext(u'Contact'),
                           form=form)


def populate_form_choices(checkout_form):
    """
    Pulls choices from the database to populate our select fields.
    """
    states = models.State.query.order_by(models.State.name).all()
    countries = models.Country.query.order_by(models.Country.name).all()
    state_names = [('', gettext(u'Please select (optional)'))]
    for state in states:
        state_names.append([str(state.id), state.name])
    #choices need to come in the form of a list comprised of enumerated lists
    #example [('cpp', 'C++'), ('py', 'Python'), ('text', 'Plain Text')]
    state_choices = state_names
    country_names = [('', '')]
    for country in countries:
        country_names.append([country.code, country.name])
    country_choices = country_names
    #now that we've built our choices, we need to set them.
    checkout_form.state.choices = state_choices
    checkout_form.country.choices = country_choices

# Checkout process
@app.route('/checkout/', methods=['GET', 'POST'])
def checkout():
    if not session['logged_in']:
        return redirect('/register')
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    page_topic = gettext(u'Checkout')
    page_content = gettext(u'Please enter your address here:')
    productlist = getProductFromSession()
    form = CheckoutForm(request.form, country='CH')
    populate_form_choices(form)
    sub_total_tmp = Decimal(0.00)
    if productlist:
        for p in productlist:
            sub_total_tmp += p.list_price
    shipping = getShipping('Shipping local')
    shipping_cost_temp = 0.00
    if shipping is not None:
        if sub_total_tmp < Decimal(150.00*session['currency_rate']):
            shipping_cost_temp = shipping.list_price * Decimal(session['currency_rate'])
            sub_total_tmp += shipping_cost_temp

    sub_total = format_currency_amount(sub_total_tmp)
    shipping_cost = format_currency_amount(shipping_cost_temp)
    if form.validate_on_submit():
        try:
            partyid = session['partyid']
            Party = Model.get('party.party')
            party = Party.find([('id', '=', partyid)])[0]
        except KeyError:
            Party = Model.get('party.party')
            party = Party()

        if party.id < 0:
            party.name = form.name.data
            Lang = Model.get('ir.lang')
            (en,) = Lang.find([('code', '=', 'en_US')])
            party.lang = en
            party.addresses[0].name = form.name.data
            party.addresses[0].street = form.street.data
            party.addresses[0].streetbis = form.street2.data
            party.addresses[0].zip = form.zip.data
            party.addresses[0].city = form.city.data
            country_id = form.country.data
            state_id = form.state.data
            Country = Model.get('country.country')
            (ch, ) = Country.find([('code', '=', country_id)])
            party.addresses[0].country = ch
            Subdivision = Model.get('country.subdivision')
            (subdivision, ) = Subdivision.find([('id', '=', state_id)])
            party.addresses[0].subdivision = subdivision
            party.addresses[0].invoice = form.invoice.data
            party.addresses[0].delivery = form.delivery.data
            party.save()
        else:
            party.addresses[0].name = form.name.data
            party.addresses[0].street = form.street.data
            party.addresses[0].streetbis = form.street2.data
            party.addresses[0].zip = form.zip.data
            party.addresses[0].city = form.city.data
            country_id = form.country.data
            state_id = form.state.data
            Country = Model.get('country.country')
            (ch, ) = Country.find([('code', '=', country_id)])
            party.addresses[0].country = ch
            Subdivision = Model.get('country.subdivision')
            (subdivision, ) = Subdivision.find([('id', '=', state_id)])
            party.addresses[0].subdivision = subdivision
            party.addresses[0].invoice = form.invoice.data
            party.addresses[0].delivery = form.delivery.data
            party.save()

        Sale = Model.get('sale.sale')
        sale = Sale()
        if (sale.id < 0):
            sale.party = party
            Currency = Model.get('currency.currency')
            (currency, ) = Currency.find([('code', '=', session['currency_code'])])
            sale.currency = currency;
            Paymentterm = Model.get('account.invoice.payment_term')
            paymentterm = Paymentterm.find([('name', '=', 'cash')])
            sale.payment_term = paymentterm[0]
            for p in productlist:
                line = sale.lines.new(quantity=1)
                line.product = p
                line.description = p.name + ' - ' + p.code
                line.quantity = 1
                line.sequence = 1
            # add shipping if needed
            if shipping_cost > Decimal(0.00):
                line = sale.lines.new(quantity=1)
                line.product = shipping
                line.description = shipping.name
                line.quantity = 1
                line.sequence = 1
            sale.save()
            session['sale_id'] = sale.id
            # remove products
            if app.config['DEACTIVATE_PRODUCT_WHEN_SOLD']:
                Product = Model.get('product.product')
                for p in productlist:
                    tmp_product = Product.find(['code', '=', p.code])
                    attribute_dict = tmp_product[0].attributes
                    for key in attribute_dict.keys():
                        if key == 'available':
                            attribute_dict[key] = False
                    tmp_product[0].attributes = attribute_dict
                    tmp_product[0].save()
        flash(gettext(u'Thank you, your address has been saved. Please proceed with the payment.'), 'success')
        return redirect('/payment')

    if form.name.data is None:
        try:
            partyid = session['partyid']
            Party = Model.get('party.party')
            party = Party.find([('id', '=', partyid)])[0]
            form.name.data = party.addresses[0].name
            form.street.data = party.addresses[0].street
            form.street2.data = party.addresses[0].streetbis
            form.zip.data = party.addresses[0].zip
            form.city.data = party.addresses[0].city
            if party.addresses[0].country:
                form.country.data = party.addresses[0].country.code
            if party.addresses[0].subdivision:
                form.state.data = str(party.addresses[0].subdivision.id)
            form.invoice.data = party.addresses[0].invoice
            form.delivery.data = party.addresses[0].delivery
        except KeyError:
            print('user is not logged in')

    return render_template('checkout.html', cart=productlist, sub_total=sub_total,
                           shipping=shipping, shipping_cost=shipping_cost, shipping_text=gettext(u'Shipping local'),
                           pt=page_topic, pc=page_content, product=productlist, title="Milliondog",
                           page=gettext(u'Checkout'), form=form)


#Paypal
@app.route('/payment/')
def payment():
    try:
        page_topic = gettext(u'Payment')
        page_content = gettext(u'Please follow the link to pay with Paypal:')
        custom = session['sale_id']
        products = getProductFromSession()
        sub_total_tmp = Decimal(0.00)
        item_name_list = []
        item_number_list = []
        amount_list = []
        for p in products:
            item_name_list.append(p.name)
            item_number_list.append(p.code)
            sub_total_tmp += p.list_price
            amount_list.append(p.list_price)
        shipping = getShipping('Shipping local')
        shipping_cost_temp = 0.00
        if shipping is not None:
            if sub_total_tmp < Decimal(150.00*session['currency_rate']):
                shipping_cost_temp = shipping.list_price * Decimal(session['currency_rate'])
                sub_total_tmp += shipping_cost_temp
        business = app.config['PAYPAL_BUSINESS']
        data = ', '.join(item_name_list)
        item_name = (data[:125] + '..') if len(data) > 127 else data
        data = ', '.join(item_number_list)
        item_number = (data[:125] + '..') if len(data) > 127 else data
        no_shipping = "0"
        TWOPLACES = Decimal(10) ** -2
        amount = (sum(amount_list)).quantize(TWOPLACES, context=Context(traps=[Inexact]))
        shipping_cost = format_currency_amount(shipping_cost_temp)
        currency_code = session['currency_code']
        hostname = app.config['PAYPAL_SHOP_DOMAIN']
        return render_template("payment.html", pt=page_topic, pc=page_content, title="Milliondog",
                               page=gettext(u'Payment'), custom=custom, business=business, item_name=item_name,
                               item_number=item_number, no_shipping=no_shipping, amount=amount,
                               currency_code=currency_code, shipping=shipping_cost, hostname=hostname)
    except Exception, e:
        return(str(e))


@app.route('/success/', methods=['POST', 'GET'])
def success():
    try:
        flash(gettext(u'PayPal payment completed successfully.'), 'success')
        session.pop('cart', None)
        session.pop('cart_item_count', None)
        return render_template("success.html")
    except Exception, e:
        return(str(e))


@app.route('/cancel/', methods=['POST', 'GET'])
def cancel():
    try:
        flash(gettext(u'PayPal payment failed.'), 'danger')
        return render_template("paymentfailed.html")
    except Exception, e:
        return(str(e))


@app.route('/testpayment/')
def testpayment():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Sale = Model.get('sale.sale')
    saleid = 15
    payment_gross = 55.00
    saleList = Sale.find(['id', '=', saleid])
    if saleList is not None:
        check_order = True
        if (saleList[0].state != 'draft'):
            check_order = False
        if (saleList[0].currency.symbol != 'CHF'):
            check_order = False

        SaleLine = Model.get('sale.line')
        saleLine = SaleLine.find(['sale', '=', saleid])
        saleTotal = Decimal(0.00)
        for n in saleLine:
            saleTotal += n.unit_price * Decimal(n.quantity)
        if (Decimal(payment_gross) < saleTotal):
            check_order = False
        if check_order:
            # change sale state to 'confirmed'
            saleList[0].comment += 'PAYPAL IPN DATA\n'+'\n'
            saleList[0].save()
            saleList[0].click('quote')
        else:
            # add note that something failed in payment
            saleList[0].comment = 'ERROR WITH PAYPAL IPN DATA\n'+'\n'
            saleList[0].save()


@app.route('/ipn/', methods=['POST'])
def ipn():
    try:
        arg = ''
        request.parameter_storage_class = ImmutableOrderedMultiDict
        values = request.form
        for x, y in values.iteritems():
            arg += "&{x}={y}".format(x=x,y=y)

        validate_url = 'https://www.sandbox.paypal.com' \
                        '/cgi-bin/webscr?cmd=_notify-validate{arg}' \
                        .format(arg=arg)
        r = requests.get(validate_url)
        if r.text == 'VERIFIED':
            try:
                payer_email = request.form.get('payer_email')
                unix = int(time.time())
                payment_date = request.form.get('payment_date')
                saleid = request.form.get('custom')
                last_name = request.form.get('last_name')
                payment_gross = request.form.get('mc_gross')
                payment_fee = request.form.get('mc_fee')
                payment_currency = request.form.get('mc_currency')
                payment_net = float(payment_gross) - float(payment_fee)
                payment_status = request.form.get('payment_status')
                txn_id = request.form.get('txn_id')
            except Exception as e:
                with open('/tmp/ipnout.txt','a') as f:
                    data = 'ERROR WITH IPN DATA\n'+str(values)+'\n'
                    f.write(data)

            with open('/tmp/ipnout.txt','a') as f:
                data = 'SUCCESS\n'+str(values)+'\n'
                f.write(data)

            # user_name, mc_gross, mc_fee, mc_currency need to be checked in database
            # mark order in tryton as paid
            # c.execute("INSERT INTO ipn (unix, payment_date, username, last_name, payment_gross, payment_fee, payment_net, payment_status, txn_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            #           (unix, payment_date, username, last_name, payment_gross, payment_fee, payment_net, payment_status, txn_id))
            config.set_trytond(DATABASE_NAME, config_file=CONFIG)
            Sale = Model.get('sale.sale')
            saleList = Sale.find(['id', '=', saleid])
            if saleList is not None:
                check_order = True
                if (saleList[0].state != 'draft'):
                    check_order = False
                if (saleList[0].currency.symbol != payment_currency):
                    check_order = False

                saleLine = saleList[0].lines
                saleTotal = Decimal(0.00)
                for n in saleLine:
                    saleTotal += n.unit_price * Decimal(n.quantity)
                if (Decimal(payment_gross) < saleTotal):
                    check_order = False
                if check_order:
                    # change sale state to 'confirmed'
                    Attachments = Model.get('ir.attachment')
                    attachment = Attachments()
                    attachment.name = 'PAYPAL IPN DATA'
                    attachment.resource = saleList[0]
                    attachment.description = 'PAYPAL IPN DATA\n'+str(values)+'\n'
                    attachment.save()
                    # saleList[0].save()
                    try:
                        saleList[0].click('quote')
                    except Exception as e:
                        print 'Exception: Could not update sale state '+str(e)
                else:
                    # add note that something failed in payment
                    Attachments = Model.get('ir.attachment')
                    attachment = Attachments()
                    attachment.name = 'PAYPAL IPN DATA'
                    attachment.resource = saleList[0]
                    attachment.description = 'ERROR WITH PAYPAL IPN DATA\n'+str(values)+'\n'
                    attachment.save()
        else:
            with open('/tmp/ipnout.txt','a') as f:
                data = 'FAILURE\n'+str(values)+'\n'
                f.write(data)

        return r.text
    except Exception as e:
        return str(e)


# footer information
@app.route("/shipping/")
def shipping():
    active_page = 'shipping'
    page_topic = gettext(u'Payment and Shipping')
    page_content = gettext(u'''<p>We accept PayPal payment only.</p><br>
        <p>Handling time: 2-3 days</p><br>
        <p>Estimate shipping time is about 4-7 working days within Switzerland, approximately 20 working days for overseas, 7.50 CHF, for all articles.</p><br>
        <p>Please feel free to contact us if you have any question. Hope you enjoy dealing with us!</p><br>
        ''')
    return render_template('generic.html', active_page=active_page, pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Payment and Shipping'))

@app.route("/returns/")
def returns():
    active_page = 'returns'
    page_topic = gettext(u'Right of revocation')
    page_content = gettext(u'''<p>Conditions of returned goods<br><br></p>
        <p>We will gladly take back your order if you are not satisfied.</p><br>
        <p>Please note, however that the goods must be in the normal conditions.</p><br>
        <p>All returns of goods that have obviously been used and that therefore can not be sold will not be accepted.</p><br>
        <p>The payment amount will be credited back to your PayPal account.</p><br>
        ''')
    return render_template('generic.html', active_page=active_page, pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Right of revocation'))

@app.route("/termsandconditions/")
def termsandconditions():
    active_page = 'termsandconditions'
    page_topic = gettext(u'Terms and conditions')
    page_content = gettext(u'''<p><strong>Allgemeine Geschäftsbedingungen mit Kundeninformationen</strong></p>
        <p>1. Geltungsbereich<br>
        2. Vertragsschluss<br>
        3. Widerrufsrecht<br>
        4. Preise und Zahlungsbedingungen<br>
        5. Liefer und Versandbedingungen<br>
        6. Mängelhaftung<br>
        7. Freistellung bei Verletzung von Drittrechten<br>
        8. Anwendbares Recht</p>
        <p><strong>1. Geltungsbereich<br>
        </strong>1.1 Diese Allgemeinen Geschäftsbedingungen (nachfolgend “AGB”) von “Milliondog” (nachfolgend “Verkäufer”), gelten für alle Verträge, die ein Verbraucher oder Unternehmer (nachfolgend “Kunde”) mit dem Verkäufer hinsichtlich der vom Verkäufer in seinem Online-Shop dargestellten Waren und/oder Leistungen abschließt. Hiermit wird der Einbeziehung von eigenen Bedingungen des Kunden widersprochen, es sei denn, es ist etwas anderes vereinbart.</p>
        <p>1.2 Verbraucher im Sinne dieser AGB ist jede natürliche Person, die ein Rechtsgeschäft zu Zwecken abschließt, die überwiegend weder ihrer gewerblichen noch ihrer selbstständigen beruflichen Tätigkeit zugerechnet werden können. Unternehmer im Sinne dieser AGB ist jede natürliche oder juristische Person oder eine rechtsfähige Personengesellschaft, die bei Abschluss eines Rechtsgeschäfts in Ausübung ihrer selbstständigen beruflichen oder gewerblichen Tätigkeit handelt.</p>
        <p><strong>2. Vertragsschluss<br>
        </strong>2.1 Die im Online-Shop des Verkäufers enthaltenen Produktdarstellungen stellen keine verbindlichen Angebote seitens des Verkäufers dar, sondern dienen zur Abgabe eines verbindlichen Angebots durch den Kunden.</p>
        <p>2.2 Der Kunde kann das Angebot über das in den Online-Shop des Verkäufers integrierte Online-Bestellformular abgeben. Dabei gibt der Kunde, nachdem er die ausgewählten Waren und/oder Leistungen in den virtuellen Warenkorb gelegt und den elektronischen Bestellprozess durchlaufen hat, durch Klicken des den Bestellvorgang abschliessenden Buttons ein rechtlich verbindliches Vertragsangebot in Bezug auf die im Warenkorb enthaltenen Waren und/oder Leistungen ab.</p>
        <p>2.3 Der Verkäufer kann das Angebot des Kunden innerhalb von fünf Tagen annehmen,<br>
        – indem er dem Kunden eine schriftliche Auftragsbestätigung oder eine Auftragsbestätigung in Textform (Fax oder E-Mail) übermittelt, wobei insoweit der Zugang der Auftragsbestätigung beim Kunden massgeblich ist, oder</p>
        <p>– indem er dem Kunden die bestellte Ware liefert, wobei insoweit der Zugang der Ware beim Kunden massgeblich ist.</p>
        <p>Liegen mehrere der vorgenannten Alternativen vor, kommt der Vertrag in dem Zeitpunkt zustande, in dem eine der vorgenannten Alternativen zuerst eintritt. Nimmt der Verkäufer das Angebot des Kunden innerhalb vorgenannter Frist nicht an, so gilt dies als Ablehnung des Angebots mit der Folge, dass der Kunde nicht mehr an seine Willenserklärung gebunden ist.</p>
        <p>2.4 Die Frist zur Annahme des Angebots beginnt am Tag nach der Absendung des Angebots durch den Kunden zu laufen und endet mit dem Ablauf des fünften Tages, welcher auf die Absendung des Angebots folgt.</p>
        <p>2.5 Bei der Abgabe eines Angebots über das Online-Bestellformular des Verkäufers wird der Vertragstext vom Verkäufer gespeichert und dem Kunden nach Absendung seiner Bestellung nebst den vorliegenden AGB in Textform (z. B. E-Mail, Fax oder Brief) zugeschickt. Zusätzlich wird der Vertragstext auf der Internetseite des Verkäufers archiviert und kann vom Kunden über sein passwortgeschütztes Kundenkonto unter Angabe der entsprechenden Login-Daten kostenlos abgerufen werden, sofern der Kunde vor Absendung seiner Bestellung ein Kundenkonto im Online-Shop des Verkäufers angelegt hat.</p>
        <p>2.6 Vor verbindlicher Abgabe der Bestellung über das Online-Bestellformular des Verkäufers kann der Kunde seine Eingaben laufend über die üblichen Tastatur- und Mausfunktionen korrigieren. Darüber hinaus werden alle Eingaben vor der verbindlichen Abgabe der Bestellung noch einmal in einem Bestätigungsfenster angezeigt und können auch dort mittels der üblichen Tastatur- und Mausfunktionen korrigiert werden.</p>
        <p>2.7 Für den Vertragsschluss steht ausschließlich die deutsche Sprache zur Verfügung.</p>
        <p>2.8 Die Bestellabwicklung und Kontaktaufnahme finden in der Regel per E-Mail und automatisierter Bestellabwicklung statt. Der Kunde hat sicherzustellen, dass die von ihm zur Bestellabwicklung angegebene E-Mail-Adresse zutreffend ist, so dass unter dieser Adresse die vom Verkäufer versandten E-Mails empfangen werden können. Insbesondere hat der Kunde bei dem Einsatz von SPAM-Filtern sicherzustellen, dass alle vom Verkäufer oder von diesem mit der Bestellabwicklung beauftragten Dritten versandten Mails zugestellt werden können.</p>
        <p><strong>3. Widerrufsrecht<br>
        </strong>Verbrauchern steht grundsätzlich ein Widerrufsrecht zu. Nähere Informationen zum Widerrufsrecht ergeben sich aus der&nbsp;<a href="http://milliondog.com/widerrufsrecht/">Widerrufsbelehrung</a>&nbsp;des Verkäufers.</p>
        <p><strong>4. Preise und Zahlungsbedingungen<br>
        </strong>4.1 Sofern sich aus dem Angebot des Verkäufers nichts anderes ergibt, handelt es sich bei den angegebenen Preisen um Endpreise, die die gesetzliche Umsatzsteuer enthalten. Gegebenenfalls zusätzlich anfallende Liefer- und Versandkosten werden in der jeweiligen Produktbeschreibung gesondert angegeben.</p>
        <p>4.2 Bei Lieferungen in Länder ausserhalb der Europäischen Union können im Einzelfall weitere Kosten anfallen, die der Verkäufer nicht zu vertreten hat und die vom Kunden zu tragen sind. Hierzu zählen beispielsweise Kosten für die Geldübermittlung durch Kreditinstitute (z.B. Überweisungsgebühren, Wechselkursgebühren) oder einfuhrrechtliche Abgaben bzw. Steuern (z.B. Zölle).</p>
        <p><strong>5. Liefer und Versandbedingungen<br>
        </strong>5.1 Die Lieferung von Waren erfolgt regelmäßig auf dem Versandwege und an die vom Kunden angegebene Lieferanschrift. Bei der Abwicklung der Transaktion, ist die in der Kaufabwicklung des Verkäufers angegebene Lieferanschrift maßgeblich. Für die Zahlungsart PayPal gilt die vom Kunden zum Zeitpunkt der Bezahlung bei PayPal hinterlegte Lieferanschrift als massgeblich.</p>
        <p>5.2 Sendet das Transportunternehmen die versandte Ware an den Verkäufer zurück, da eine Zustellung beim Kunden nicht möglich war, trägt der Kunde die Kosten für den erfolglosen Versand. Dies gilt nicht, wenn er den Umstand, der zur Unmöglichkeit der Zustellung geführt hat, nicht zu vertreten hat oder wenn er vorübergehend an der Annahme der angebotenen Leistung verhindert war, es sei denn, dass der Verkäufer ihm die Leistung eine angemessene Zeit vorher angekündigt hatte.</p>
        <p><strong>6. Mängelhaftung<br>
        </strong>Es gilt die gesetzliche Mängelhaftung</p>
        <p><strong>7. Freistellung bei Verletzung von Drittrechten<br>
        </strong>Schuldet der Verkäufer nach dem Inhalt des Vertrages neben der Warenlieferung auch die Verarbeitung der Ware nach bestimmten Vorgaben des Kunden, hat der Kunde sicherzustellen, dass die dem Verkäufer von ihm zum Zwecke der Verarbeitung überlassenen Inhalte nicht die Rechte Dritter (z. B. Urheberrechte oder Markenrechte) verletzen. Der Kunde stellt den Verkäufer von Ansprüchen Dritter frei, die diese im Zusammenhang mit einer Verletzung ihrer Rechte durch die vertragsgemässe Nutzung der Inhalte des Kunden durch den Verkäufer diesem gegenüber geltend machen können. Der Kunde übernimmt hierbei auch die angemessenen Kosten der notwendigen Rechtsverteidigung einschliesslich aller Gerichts- und Anwaltskosten in gesetzlicher Höhe. Dies gilt nicht, wenn die Rechtsverletzung vom Kunden nicht zu vertreten ist. Der Kunde ist verpflichtet, dem Verkäufer im Falle einer Inanspruchnahme durch Dritte unverzüglich, wahrheitsgemäss und vollständig alle Informationen zur Verfügung zu stellen, die für die Prüfung der Ansprüche und eine Verteidigung erforderlich sind.</p>
        <p><strong>8. Anwendbares Recht<br>
        </strong>8.1 Für sämtliche Rechtsbeziehungen der Parteien gilt das Recht der Schweiz, unter Ausschluss der Gesetze über den internationalen Kauf beweglicher Waren. Bei Verbrauchern gilt diese Rechtswahl nur insoweit, als nicht der gewährte Schutz durch zwingende Bestimmungen des Rechts des Staates, in dem der Verbraucher seinen gewöhnlichen Aufenthalt hat, entzogen wird.</p>
        ''')
    return render_template('generic.html', active_page=active_page, pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Terms and conditions'))

@app.route("/privacy/")
def privacy():
    active_page = 'privacy'
    page_topic = gettext(u'Disclaimer')
    page_content = gettext(u'''<p><strong>Der Schutz Ihrer Privatsphäre ist uns ein wichtiges Anliegen. Bitte beachten Sie die folgenden Punkte unserer Datenschutzerklärung.</strong></p>
        <p><strong>Geltungsbereich<br>
        </strong>Diese Datenschutzerklärung klärt Nutzer über die Art, den Umfang und Zwecke der Erhebung und Verwendung personenbezogener Daten durch den verantwortlichen Anbieter Sabine Reiss und Anke Siegrist, Obere Rebbergstrasse 34, CH-4800 Zofingen , Telefon: +41 62 752 40 48, E-Mail: informme@milliondog.com auf dieser Website (im folgenden “Angebot”) auf.</p>
        <p>Das Bundesgesetz über den Datenschutz (DSG) bildet die Grundlage dieser Datenschutzerklärung.</p>
        <p>&nbsp;</p>
        <p><strong>Zugriffsdaten/ Server-Logfiles<br>
        </strong>Der Anbieter (beziehungsweise sein Webspace-Provider) erhebt Daten über jeden Zugriff auf das Angebot (so genannte Serverlogfiles). Zu den Zugriffsdaten gehören:</p>
        <p>Name der abgerufenen Webseite, Datei, Datum und Uhrzeit des Abrufs, übertragene Datenmenge, Meldung über erfolgreichen Abruf, Browsertyp nebst Version, das Betriebssystem des Nutzers, Referrer URL (die zuvor besuchte Seite), IP-Adresse und der anfragende Provider.</p>
        <p>Der Anbieter verwendet die Protokolldaten nur für statistische Auswertungen zum Zweck des Betriebs, der Sicherheit und der Optimierung des Angebotes. Der Anbieterbehält sich jedoch vor, die Protokolldaten nachträglich zu überprüfen, wenn aufgrund konkreter Anhaltspunkte der berechtigte Verdacht einer rechtswidrigen Nutzung besteht.</p>
        <p>&nbsp;</p>
        <p><strong>Umgang mit personenbezogenen Daten<br>
        </strong>Personenbezogene Daten sind Informationen, mit deren Hilfe eine Person bestimmbar ist, also Angaben, die zurück zu einer Person verfolgt werden können. Dazu gehören der Name, die Emailadresse oder die Telefonnummer. Aber auch Daten über Vorlieben, Hobbies, Mitgliedschaften oder welche Webseiten von jemandem angesehen wurden zählen zu personenbezogenen Daten.</p>
        <p>Personenbezogene Daten werden von dem Anbieter nur dann erhoben, genutzt und weiter gegeben, wenn dies gesetzlich erlaubt ist oder die Nutzer in die Datenerhebung einwilligen.</p>
        <p>&nbsp;</p>
        <p><strong>Kontaktaufnahme<br>
        </strong>Bei der Kontaktaufnahme mit dem Anbieter (zum Beispiel per Kontaktformular oder E-Mail) werden die Angaben des Nutzers zwecks Bearbeitung der Anfrage sowie für den Fall, dass Anschlussfragen entstehen, gespeichert.</p>
        <p>&nbsp;</p>
        <p><strong>Kommentare und Beiträge<br>
        </strong>Wenn Nutzer Kommentare im Blog oder sonstige Beiträge hinterlassen, werden ihre IP-Adressen gespeichert. Das erfolgt zur Sicherheit des Anbieters, falls jemand in Kommentaren und Beiträgen widerrechtliche Inhalte schreibt (Beleidigungen, verbotene politische Propaganda, etc.). In diesem Fall kann der Anbieter selbst für den Kommentar oder Beitrag belangt werden und ist daher an der Identität des Verfassers interessiert.</p>
        <p>&nbsp;</p>
        <p><strong>Cookies<br>
        </strong>Cookies sind kleine Dateien, die es ermöglichen, auf dem Zugriffsgerät der Nutzer (PC, Smartphone o.ä.) spezifische, auf das Gerät bezogene Informationen zu speichern. Sie dienen zum einem der Benutzerfreundlichkeit von Webseiten und damit den Nutzern (z.B. Speicherung von Logindaten). Zum anderen dienen sie, um die statistische Daten der Webseitennutzung zu erfassen und sie zwecks Verbesserung des Angebotes analysieren zu können. Die Nutzer können auf den Einsatz der Cookies Einfluss nehmen. Die meisten Browser verfügen eine Option mit der das Speichern von Cookies eingeschränkt oder komplett verhindert wird. Allerdings wird darauf hingewiesen, dass die Nutzung und insbesondere der Nutzungskomfort ohne Cookies eingeschränkt werden.</p>
        <p>Sie können viele Online-Anzeigen-Cookies von Unternehmen über die US-amerikanische Seite <a href="http://www.aboutads.info/choices/">http://www.aboutads.info/choices/</a> oder die EU-Seite <a href="http://www.youronlinechoices.com/uk/your-ad-choices/ ">http://www.youronlinechoices.com/uk/your-ad-choices/ </a> verwalten.</p>
        <p>&nbsp;</p>
        <p><strong>Registrierfunktion<br>
        </strong>Die im Rahmen der Registrierung eingegebenen Daten werden für die Zwecke der Nutzung des Angebotes verwendet. Die Nutzer können über angebots- oder registrierungsrelevante Informationen, wie Änderungen des Angebotsumfangs oder technische Umstände per E-Mail informiert werden. Die erhobenen Daten sind aus der Eingabemaske im Rahmen der Registrierung ersichtlich. Dazu gehören Name, postalische Adresse, E-Mail-Adresse.</p>
        <p>&nbsp;</p>
        <p><strong>Google Analytics<br>
        </strong>Dieses Angebot benutzt Google Analytics, einen Webanalysedienst der Google Inc. („Google“). Google Analytics verwendet sog. „Cookies“, Textdateien, die auf Computer der Nutzer gespeichert werden und die eine Analyse der Benutzung der Website durch sie ermöglichen. Die durch den Cookie erzeugten Informationen über Benutzung dieser Website durch die Nutzer werden in der Regel an einen Server von Google in den USA übertragen und dort gespeichert.</p>
        <p>Im Falle der Aktivierung der IP-Anonymisierung auf dieser Webseite, wird die IP-Adresse der Nutzer von Google jedoch innerhalb von Mitgliedstaaten der Europäischen Union oder in anderen Vertragsstaaten des Abkommens über den Europäischen Wirtschaftsraum zuvor gekürzt. Nur in Ausnahmefällen wird die volle IP-Adresse an einen Server von Google in den USA übertragen und dort gekürzt. Die IP-Anonymisierung ist auf dieser Website aktiv. Im Auftrag des Betreibers dieser Website wird Google diese Informationen benutzen, um die Nutzung der Website durch die Nutzer auszuwerten, um Reports über die Websiteaktivitäten zusammenzustellen und um weitere mit der Websitenutzung und der Internetnutzung verbundene Dienstleistungen gegenüber dem Websitebetreiber zu erbringen.</p>
        <p>Die im Rahmen von Google Analytics von Ihrem Browser übermittelte IP-Adresse wird nicht mit anderen Daten von Google zusammengeführt. Die Nutzer können die Speicherung der Cookies durch eine entsprechende Einstellung Ihrer Browser-Software verhindern; Dieses Angebot weist die Nutzer jedoch darauf hin, dass Sie in diesem Fall gegebenenfalls nicht sämtliche Funktionen dieser Website vollumfänglich werden nutzen können. Die Nutzer können darüber hinaus die Erfassung der durch das Cookie erzeugten und auf ihre Nutzung der Website bezogenen Daten (inkl. Ihrer IP-Adresse) an Google sowie die Verarbeitung dieser Daten durch Google verhindern, indem sie das unter dem folgenden Link verfügbare Browser-Plugin herunterladen und installieren: <a href="http://tools.google.com/dlpage/gaoptout?hl=de">http://tools.google.com/dlpage/gaoptout?hl=de</a>.</p>
        <p>Alternativ zum Browser-Add-On oder innerhalb von Browsern auf mobilen Geräten, <a id="GAOptOut" title="Google Analytics Opt-Out-Cookie setzen" href="javascript:gaOptout()">klicken Sie bitte diesen Link</a>, um die Erfassung durch Google Analytics innerhalb dieser Website zukünftig zu verhindern. Dabei wird ein Opt-Out-Cookie auf Ihrem Gerät abgelegt. Löschen Sie Ihre Cookies, müssen Sie diesen Link erneut klicken.</p>
        <p>&nbsp;</p>
        <p><strong>Widerruf, Änderungen, Berichtigungen und Aktualisierungen<br>
        </strong>Der Nutzer hat das Recht, auf Antrag unentgeltlich Auskunft zu erhalten über die personenbezogenen Daten, die über ihn gespeichert wurden. Zusätzlich hat der Nutzer das Recht auf Berichtigung unrichtiger Daten, Sperrung und Löschung seiner personenbezogenen Daten, soweit dem keine gesetzliche Aufbewahrungspflicht entgegensteht.</p>
        ''')
    return render_template('generic.html', active_page=active_page, pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Disclaimer'))

@app.route("/legal/")
def legal():
    active_page = 'legal'
    page_topic = gettext(u'Legal notice')
    page_content = gettext(u'''<p>
        MillionDog<br>
        Inhaber: Sabine Reiss und Anke Siegrist<br>
        Obere Rebbergstrasse 34<br>
        CH-4800 Zofingen<br>
        e-mail: informme@milliondog.com<br><br>
        All contents on www.milliondog are owned by Milliondog and copyright protected. Any use of milliondog`s contents, including pictures, texts and intellectual property needs strictly consent by Milliondog</p>
        ''')
    return render_template('generic.html', active_page=active_page, pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Legal notice'))
