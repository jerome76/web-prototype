# -*- coding: utf-8 -*-
from flask_shop import app, models
from flask import Flask, jsonify, request
from proteus import config, Model, Wizard, Report
from datetime import date, datetime
import time
import decimal
import json
import urlparse
from escpos import *
import psycopg2

CONFIG = app.config['TRYTON_CONFIG_FILE']
DATABASE_NAME = app.config['TRYTON_DATABASE_NAME']
config.set_trytond(DATABASE_NAME, config_file=CONFIG)


def getProductDirect(hideoutofstockitems):
    category_condition = 'and 1 = 1 '
    size_condition = 'and 1 = 1 '
    outofstock_condition = 'and 1 = 1 '
    if hideoutofstockitems == 'True':
        outofstock_condition = "and product.attributes like '%\"available\": true%' "
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
                    "where product.template = t.id "
                    "and t.sale_uom = uom.id " +
                    "and p.res = 'product.template,'||t.id " +
                    "and p.field = (select f.id from ir_model_field f, ir_model m "
                    "       where m.model = 'product.template' and m.id = f.model and f.name = 'list_price') " +
                    "and t.id = ptpc.template " +
                    category_condition +
                    size_condition +
                    outofstock_condition +
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
            row['list_price'] = p[10]
            row['category'] = p[11]
            result.append(row)
        print result
    except psycopg2.DatabaseError, e:
        print 'Error %s' % e
    finally:
        if con:
            con.close()
    return result

@app.route("/pos/customers/", methods=['GET'])
def get_customers():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    customers = models.Customer.query.order_by(models.Customer.name).all()
    list = []
    for c in customers:
        list.append({'id': str(c.id), 'city': c.city, 'name': c.name, 'zip': c.zip, 'country': c.country,
                     'subdivision': c.subdivision, 'street': c.street, 'streetbis': c.streetbis, 'active': c.active,
                     'delivery': c.delivery, 'invoice': c.invoice })
    return jsonify(result=list)


@app.route("/pos/categories/", methods=['GET'])
def get_categories():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    categories = models.Categories.query.order_by(models.Categories.name).all()
    list = []
    for c in categories:
        list.append({'id': str(c.id), 'name': c.name, 'parent': str(c.parent) })
    return jsonify(result=list)


@app.route("/pos/products/<hideoutofstockitems>", methods=['GET'])
def get_products(hideoutofstockitems='False'):
    products = getProductDirect(hideoutofstockitems)
    list = []
    for p in products:
        list.append({'id': p['id'], 'code': p['code'], 'category': p['category'], 'name': p['name'], 'price': p['list_price'],
                     'uom_id': p['uom_id'], 'uom_name': p['uom_name'], 'uom_symbol': p['uom_symbol'],
                     'uom_rounding': p['uom_rounding']})
    return jsonify(result=list)


@app.route("/pos/currency/", methods=['GET'])
def get_currency():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    CurrencyRate = Model.get('currency.currency.rate')
    currency_rate = CurrencyRate.find(['id', '>', 0])
    list = []
    for n in currency_rate:
        list.append({'id': str(n.id), 'code': n.currency.code, 'symbol': n.currency.symbol, 'name': n.currency.name,
                     'rate': str(n.rate), 'date': str(n.date)})
    return jsonify(result=list)


@app.route('/pos/product/<productid>')
def search_product(productid=None):
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Product = Model.get('product.product')
    product = Product.find(['code', '=', productid])
    list = []
    for n in product:
        list.append({'id': str(n.id), 'code': n.code, 'name': n.name, 'price': str(n.list_price)})
    return jsonify(result=list)


@app.route("/pos/sale/", methods=['GET', 'POST'])
def make_sale():
    print_payslip = False
    payslip = request.get_json(force=True)
    payslip_customer = payslip['customer']
    payslip_info = payslip['payslip_info']
    payslip_items = payslip['items']
    # create sale order
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Party = Model.get('party.party')
    partylist = Party.find([('id', '=', payslip_customer['customerid'])])
    party = partylist[0]
    Sale = Model.get('sale.sale')
    sale = Sale()
    if (sale.id < 0):
        sale.party = party
        sale.reference = '[' + payslip_info['username'] + '] - ' + payslip_info['order_date']
        sale.number = payslip_info['order_id']
        Currency = Model.get('currency.currency')
        (currency, ) = Currency.find([('code', '=', payslip_info['currency'])])
        sale.currency = currency
        sale.description = 'uuid: ' + payslip_info['payslip_uuid']
        # check if sale has been processed
        SaleOld = Model.get('sale.sale')
        saleold = SaleOld.find([('description', '=', 'uuid: ' + payslip_info['payslip_uuid'])])
        if len(saleold) > 0:
            print('Order has already been processed.')
            listold = [{'id': str(saleold[0].id), 'party': str(saleold[0].party.id)}]
            return jsonify(result=listold)
        sale.sale_date = date.today()
        Paymentterm = Model.get('account.invoice.payment_term')
        paymentterm = Paymentterm.find([('name', '=', 'cash')])
        sale.payment_term = paymentterm[0]
        for payslip_line in payslip_items:
            Product = Model.get('product.product')
            product = Product.find(['id', '=', payslip_line['id']])
            # remove products
            if app.config['DEACTIVATE_PRODUCT_WHEN_SOLD']:
                attribute_dict = product[0].attributes
                if attribute_dict is not None:
                    for key in attribute_dict.keys():
                        if key == 'available':
                            attribute_dict[key] = False
                    product[0].attributes = attribute_dict
                    product[0].save()
            line = sale.lines.new(quantity=1)
            line.product = product[0]
            line.description = product[0].name
            line.quantity = 1
            line.sequence = 1
        sale.save()
        try:
            sale.click('quote')
            sale.click('confirm')
            sale.click('process')
        except Exception, e:
            print 'make_sale.Exception %s' % e
        saleId = sale.id

    if print_payslip:
        # max line: Epson.text("012345678901234567890123456789012345678901\n")
        Epson = printer.Usb(0x04b8,0x0202)
        # Print image
        Epson.text("\n\n")
        with app.open_resource('logo.gif') as f:
            Epson.image(f)
        # Print Header
        Epson.text("\n\n")
        Epson.set(align='center')
        Epson.text("Milliondog - the cosy company\n")
        Epson.text(time.strftime('%X %x %Z')+"\n")
        # Print text
        Epson.set(align='left')
        Epson.text("\n\n")
        Epson.text("Pos  Beschreibung                Betrag   \n")
        Epson.text("                                          \n")
        total = decimal.Decimal(0.00)
        for counter, payslip_line in enumerate(payslip):
            pos_left = str(counter) + "  " + payslip_line['code'] + " " + payslip_line['name']
            pos_right = payslip_line['price'] + " CHF\n"
            Epson.text(pos_left + pos_right.rjust(42 - len(pos_left)))
            total = total + decimal.Decimal(payslip_line['price'])
        Epson.text("                                          \n")
        Epson.text("------------------------------------------\n")
        payslip_total = str(total) + " CHF\n"
        Epson.text("Total :   " + payslip_total.rjust(42 - 10))
        # Print text
        Epson.text("\n\n")
        Epson.set(font='b', align='center')
        Epson.text("Powered by Semilimes\n")
        # Cut paper
        Epson.text("\n\n")
        Epson.cut()

    # create response
    SaleResult = Model.get('sale.sale')
    saleResult = SaleResult.find(['id', '=', saleId])
    list = []
    for n in saleResult:
        list.append({'id': str(n.id), 'party': str(n.party.id)})
    return jsonify(result=list)


@app.route('/masterdata/state')
def masterdata_state():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    Country = Model.get('country.country')
    country = Country.find(['id', '>', 0])
    resultlist = ['states[0]=""']
    counter = 0
    for n in country:
        State = Model.get('country.subdivision')
        state = State.find(['country', '=', n.id])
        statelist = []
        # print(n.name)
        for m in state:
            statelist.append('"' + m.name + '|' + str(m.id) + '"')
            # print(m.name)
        counter += 1
        if len(statelist) > 0:
            resultlist.append('states[' + str(counter) + ']=[' + (', '.join(statelist)) + ']')
        else:
            resultlist.append('states[' + str(counter) + ']=""')
    result = ('\n'.join(resultlist))
    print result
    return result
