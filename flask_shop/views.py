# -*- coding: utf-8 -*-
from flask import Flask, render_template, flash, redirect, session, url_for, request, g
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
from decimal import *
import psycopg2
import urlparse
from passlib.hash import pbkdf2_sha256
from validate_email import validate_email

CONFIG = "./tryton.conf"
DATABASE_NAME = "tryton_dev"
config.set_trytond(DATABASE_NAME, config_file=CONFIG)

def getProductDirect(category=None, size=None):
    if category is None:
        category_condition = 'and 1 = 1 '
    else:
        category_condition = "and pc.name like '%" + category + "%' "
    if size is None:
        size_condition = 'and 1 = 1 '
    else:
        size_condition = "and product.attributes like '%" + size + "%' "
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
                    "and p.field = 757 " +
                    "and t.id = ptpc.template " +
                    category_condition +
                    size_condition +
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
            row['list_price'] = '{:20,.2f}'.format(Decimal(p[10]) * Decimal(session['currency_rate']))
            row['category'] = p[11]
            result.append(row)
        print result
    except psycopg2.DatabaseError, e:
        print 'Error %s' % e
    finally:
        if con:
            con.close()
    return result

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
def before_request():
    g.user = current_user
    g.user.locale = get_locale()

def getProductFromSession():
    try:
        cart = session['cart']
        products = []
        for p in cart:
            Product = Model.get('product.product')
            product = Product.find(['id', '=', p])
            if product is not None:
                products.append(product[0])
        return products
    except KeyError:
        print("cart is empty.")
        return None


@app.route("/about/")
def about():
    page_topic = gettext(u'About us')
    page_content = gettext(u'''
                We created Milliondog because we love dogs. Milliondog symbolizes the importance of a dog for his owner and our philosophy reflects just that. Each Milliondog Cosy is unique in material and colour and emphasises the individual personality and uniqueness of your pawesome darling.
                <br><br>We love our work and you can see this in every Cosy.
                ''')
    return render_template('about.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('About us'))

@app.route("/sendus/")
def sendus():
    page_topic = gettext(u'Send us')
    page_content = gettext(u'''
                <br>We welcome your enquiries regarding our exclusive service using your own fabrics, for example we can use material from your children’s, parent’s or partner’s clothes to make a special Milliondog-Cosy for your dog. Get in touch with us so we can work together to give your dog a unique look.
                <br>Let your dog play his own part by wearing a Milliondog-Cosy at a special day in your life.
                <br>For more information contact us by Email
                ''')
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
    list_price = '{:20,.2f}'.format(product[0].list_price * Decimal(session['currency_rate']))
    return render_template('product.html', pt=page_topic, pc=page_content, product=product[0], list_price=list_price,
                           title="Milliondog", page=gettext('Product'))

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
    page_content = gettext(u'Shop:')
    start = time.time()
    # fastproducts = models.Product.query.all()
    directproducts = getProductDirect(category, size)
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
    return render_template('productcategories.html', db_model='Product Categories', db_list=idlist, title="Milliondog", page='Product Categories')



@app.route('/cart/')
def cart():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    User = Model.get('res.user')
    user = User.find(['id', '=', '1'])
    cart = getProductFromSession()
    session['user_name'] = 'paypal_testuser'
    return render_template('cart.html', message=user[0].name, id=user[0].id, cart=cart, title="Milliondog", page='Cart')


@app.route('/cart/add/<productid>')
def cart_add(productid=None):
    cart = []
    try:
        cart = session['cart']
    except KeyError:
        session['cart'] = cart
    if productid not in cart:
        cart.append(productid)
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
def admin():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    User = Model.get('res.user')
    user = User.find(['id', '=', '1'])
    Party = Model.get('party.party')
    partyList = Party.find(['id', '>=', '0'])
    Stock = Model.get('stock.move')
    stocklist = Stock.find(['id', '>=', '0'])
    Product = Model.get('product.product')
    productlist = Product.find(['id', '>=', '0'])
    Sale = Model.get('sale.sale')
    salelist = Sale.find(['id', '>=', '0'])
    Invoice = Model.get('account.invoice')
    invoicelist = Invoice.find(['id', '>=', '0'])
    return render_template('account.html', message=user[0].name,
                           id=user[0].id, db_list=partyList, invoice_list=invoicelist, sale_list=salelist, stock_list=stocklist, product_list=productlist, title="Milliondog", page='Account')


@app.route('/setlang/<language>')
def setlang(language=None):
    setattr(g, 'lang_code', language)
    session['lang_code'] = language
    refresh()
    return redirect("/")

@app.route('/setcurrency/<currency>')
def setcurrency(currency=None):
    setattr(g, 'currency_code', currency)
    session['currency_code'] = currency
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    CurrencyRate = Model.get('currency.currency.rate')
    currency_rate = CurrencyRate.find(['id', '>', 0])
    for n in currency_rate:
        if n.currency.code == currency:
            session['currency_rate'] = float(n.rate)
    return redirect("/")

@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        is_valid = validate_email(form.email.data)
        if is_valid:
            flash('Login requested for name="%s", remember_me=%s' %
                  (form.email.data, str(form.remember_me.data)))
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
                    flash(gettext(u'login successful.'))
                    print('login successful in ' + str(end-start) + ' msec.')
                    session['email'] = user[0].email
                    session['userid'] = user[0].id
                    session['partyid'] = user[0].name.split(",")[1]
                    session['logged_in'] = True
                else:
                    flash(gettext(u'invalid email or password.'))
                    print('login failed: invalid password')
            else:
                flash(gettext(u'invalid email or password.'))
                print('No user found with login ' + form.email.data)
        else:
            flash(gettext(u'Invalid email address given.'))
            print('login failed: invalid email')
    return render_template('login.html',
                           title="Milliondog", page=gettext('Sign in'), form=form)

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
                flash(gettext(u'Email address already registered.'))
                print('Email address ' + form.email.data + ' already registered.')
            else:
                flash('Login requested for email="%s", remember_me=%s' %
                      (form.email.data, str(form.remember_me.data)))
                config.set_trytond(DATABASE_NAME, config_file=CONFIG)
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
                    party.name = form.name.data
                    Lang = Model.get('ir.lang')
                    (en,) = Lang.find([('code', '=', 'en_US')])
                    party.lang = en
                    party.save()
                    user.name = 'party,' + str(party.id)
                    user.save()
                    flash('Registration successful for email="%s", remember_me=%s' %
                          (form.email.data, str(form.remember_me.data)))
                    session['email'] = user.email
                    session['partyid'] = party.id
                    session['userid'] = user.id
                    session['logged_in'] = True
                else:
                    flash(gettext(u'System is down.'))
                    print('Cannot register email ' + form.email.data)
        else:
            flash(gettext(u'Invalid email address given.'))
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
        flash(gettext(u'Thank you for your message.'))
        msg = Message("Neue Nachricht über milliondog.com Kontaktformular",
                  sender="milliondog.com@gmail.com",
                  recipients=["milliondog.com@gmail.com"])
        msg.body = ('Name: %s\nEmail: %s\nBetreff: %s\n Nachricht: %s\n' %
                    (form.name.data, form.email.data, form.subject.data, form.message.data))
        msg.html = ('<b>Formularfelder</b><br>Name: %s<br>Email: %s<br>Betreff: %s<br> Nachricht: %s<br>' %
                    (form.name.data, form.email.data, form.subject.data, form.message.data))
        app.mail.send(msg)
    return render_template('contact.html',
                           pt=page_topic, pc=page_content, title="Milliondog", page=gettext(u'Contact'),
                           form=form)

# Checkout process
@app.route('/checkout/', methods=['GET', 'POST'])
def checkout():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    page_topic = gettext(u'Checkout')
    page_content = gettext(u'Please enter your address here:')
    productlist = getProductFromSession()
    form = CheckoutForm()
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
            Country = Model.get('country.country')
            (ch, ) = Country.find([('code', '=', 'CH')])
            party.addresses[0].country = ch
            # address.subdivision = None
            party.addresses[0].invoice = form.invoice.data
            party.addresses[0].delivery = form.delivery.data
            party.save()
        else:
            party.addresses[0].name = form.name.data
            party.addresses[0].street = form.street.data
            party.addresses[0].streetbis = form.street2.data
            party.addresses[0].zip = form.zip.data
            party.addresses[0].city = form.city.data
            Country = Model.get('country.country')
            (ch, ) = Country.find([('code', '=', 'CH')])
            party.addresses[0].country = ch
            # address.subdivision = None
            party.addresses[0].invoice = form.invoice.data
            party.addresses[0].delivery = form.delivery.data
            party.save()

        Sale = Model.get('sale.sale')
        sale = Sale()
        if (sale.id < 0):
            sale.party = party
            Paymentterm = Model.get('account.invoice.payment_term')
            paymentterm = Paymentterm.find([('name', '=', 'cash')])
            sale.payment_term = paymentterm[0]
            for p in productlist:
                line = sale.lines.new(quantity=1)
                line.product = p
                line.description = p.name + ' - ' + p.code
                line.quantity = 1
                line.sequence = 1
            sale.save()
            session['sale_id'] = sale.id
        flash('Checkout started successfully name="%s", name2=%s, saleid=%s' %
              (form.name.data, str(form.name2.data), sale.id))

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
            form.invoice.data = party.addresses[0].invoice
            form.delivery.data = party.addresses[0].delivery
        except KeyError:
            print('user is not logged in')

    return render_template('checkout.html',
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
        item_name_list = []
        item_number_list = []
        amount_list = []
        for p in products:
            item_name_list.append(p.name)
            item_number_list.append(p.code)
            amount_list.append(p.list_price)
        business = "express3.com-facilitator@gmail.com"
        item_name = ', '.join(item_name_list)
        item_number = ', '.join(item_number_list)
        no_shipping = "0"
        TWOPLACES = Decimal(10) ** -2
        amount = (sum(amount_list)).quantize(TWOPLACES, context=Context(traps=[Inexact]))
        currency_code = "CHF"
        shipping_cost = "3.50"
        hostname = "http://85.7.120.190:5000"
        return render_template("payment.html", pt=page_topic, pc=page_content, title="Milliondog",
                               page=gettext(u'Payment'), custom=custom, business=business, item_name=item_name,
                               item_number=item_number, no_shipping=no_shipping, amount=amount,
                               currency_code=currency_code, shipping=shipping_cost, hostname=hostname)
    except Exception, e:
        return(str(e))


@app.route('/success/', methods=['POST', 'GET'])
def success():
    try:
        flash('Paypal payment completed successfully.')
        return render_template("success.html")
    except Exception, e:
        return(str(e))

@app.route('/cancel/', methods=['POST', 'GET'])
def cancel():
    try:
        flash('Paypal payment failed..')
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
    page_topic = gettext(u'Payment and Shipping')
    page_content = gettext(u'''
                Payment & Shipping<br>
                We accept PayPAL payment only.<br>
                Handling time: 2-3 days<br>
                Estimate shipping time is about 4-7 working days within Switzerland, approximately 20 working days for overseas, 7.50 CHF, for all articles.<br>
                Please feel free to contact us if you have any question. Hope you enjoy dealing with us!<br>
                ''')
    return render_template('generic.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Payment and Shipping'))

@app.route("/returns/")
def returns():
    page_topic = gettext(u'Right of revocation')
    page_content = gettext(u'''
                Right of revocation<br>
                Conditions of returned goods<br>
                We will gladly take back your order if you are not satisfied.<br>
                Please note, however that the goods must be in the normal conditions.<br>
                All returns of goods that have obviously been used and that therefore can not be sold will not be accepted.<br>
                The payment amount will be credited back to your PayPal account.<br>
                ''')
    return render_template('generic.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Right of revocation'))

@app.route("/termsandconditions/")
def termsandconditions():
    page_topic = gettext(u'General terms and conditions')
    page_content = gettext(u'''
        Terms & Conditions<br><br>
        Allgemeine Geschäftsbedingungen mit Kundeninformationen<br>

        1. Geltungsbereich<br>
        2. Vertragsschluss<br>
        3. Widerrufsrecht<br>
        4. Preise und Zahlungsbedingungen<br>
        5. Liefer und Versandbedingungen<br>
        6. Mängelhaftung<br>
        7. Freistellung bei Verletzung von Drittrechten<br>
        8. Anwendbares Recht<br>
                ''')
    return render_template('generic.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('General terms and conditions'))

@app.route("/privacy/")
def privacy():
    page_topic = gettext(u'Privacy Statment')
    page_content = gettext(u'<br>')
    return render_template('generic.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Privacy Statment'))

@app.route("/legal/")
def legal():
    page_topic = gettext(u'Legal notice')
    page_content = gettext(u'''Legal notice<br><br>
                                MillionDog<br>
                                CH-4800 Zofingen<br>
                                e-mail: informme@milliondog.com<br>
                                All contents on www.milliondog are owned by Milliondog and copyright protected. Any use of milliondog`s contents, including pictures, texts and intellectual property needs strictly consent by Milliondog
                ''')
    return render_template('generic.html', pt=page_topic, pc=page_content, title="Milliondog", page=gettext('Legal notice'))
