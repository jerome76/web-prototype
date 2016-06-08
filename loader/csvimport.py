from proteus import config, Model, Wizard, Report
import csv
from decimal import *
from flask_shop import app
from datetime import date


def load_internal_shipment(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for internal shipment')
        readertest = csv.DictReader(f)
        for row in readertest:
            print(row['Price'], row['Shipping'], row['Manufacturer'], row['ArtNumber'])

        print('Start import')
        StockShipmentInternal = Model.get('stock.shipment.internal')
        stockshipmentinternal = StockShipmentInternal()
        stockshipmentinternal.reference = filename
        LocationFrom = Model.get('stock.location')
        locationfrom = LocationFrom.find([('code', '=', 'IN')])
        stockshipmentinternal.from_location = locationfrom[0]
        LocationTo = Model.get('stock.location')
        locationto = LocationTo.find([('code', '=', 'STO')])
        stockshipmentinternal.to_location = locationto[0]
        stockshipmentinternal.effective_date = date.today()
        stockshipmentinternal.save()
        reader = csv.DictReader(f)
        moves = []
        if stockshipmentinternal.id > 0:
            for row in reader:
                print(row['Price'], row['Shipping'], row['Manufacturer'])
                StockMove = Model.get('stock.move')
                stockmove = StockMove()
                stockmove.shipment = stockshipmentinternal
                Product = Model.get('product.product')
                product = Product.find([('code', '=', row['ArtNumber'])])
                stockmove.product = product[0]
                stockmove.quantity = 1
                stockmove.from_location = locationfrom[0]
                stockmove.to_location = locationto[0]
                stockmove.effective_date = date.today()
                stockmove.planned_date = date.today()
                stockmove.unit_price = Decimal(0.000)
                stockmove.cost_price = product[0].cost_price
                stockmove.save()
                moves.append(stockmove)
    finally:
        f.close()


def import_customers(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for customers')
        readertest = csv.DictReader(f)
        for row in readertest:
            print(row['country_code'], row['first_name'], row['last_name'], row['company_name'])

        print('Start import')
        reader = csv.DictReader(f)
        for row in reader:
            countrycode = row['country_code']
            Lang = Model.get('ir.lang')
            (en,) = Lang.find([('code', '=', 'en_US')])
            Country = Model.get('country.country')
            (cc,) = Country.find([('code', '=', countrycode)])
            print(row['first_name'], row['last_name'], row['company_name'], row['country_code'])
            Party = Model.get('party.party')
            party = Party()
            if party.id < 0:
                party.name = row['company_name']
                party.lang = en
                party.addresses[0].name = row['first_name']+' '+row['last_name']
                party.addresses[0].street = row['address']
                party.addresses[0].streetbis = None
                party.addresses[0].zip = row['zip']
                party.addresses[0].city = row['city']
                party.addresses[0].country = cc
                # party.addresses[0].subdivision = row['state']
                party.addresses[0].invoice = True
                party.addresses[0].delivery = True
                party.save()
    finally:
        f.close()


def import_products(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for products')
        readertest = csv.DictReader(f)
        for row in readertest:
            print(row['Price'], row['Title'], row['ArtNumber'], row['Description'], row['Price'], row['CostPrice'])

        print('Start import')
        Default_uom = Model.get('product.uom')
        default_uom = Default_uom.find([('symbol', '=', 'u')])
        Category = Model.get('product.category')
        category = Category.find([('name', '=', 'Cosy')])
        Attributeset = Model.get('product.attribute.set')
        attributeset = Attributeset.find([('name', '=', 'default_webshop')])
        reader = csv.DictReader(f)
        for row in reader:
            print(row['Price'], row['Shipping'], row['Manufacturer'])
            Product = Model.get('product.product')
            product = Product()
            Producttemplate = Model.get('product.template')
            producttemplatelist = Producttemplate.find([('name', '=', row['Title'])])
            if producttemplatelist is None:
                producttemplate = Producttemplate()
            else:
                producttemplate = producttemplatelist[0]
            producttemplate.accounts_category = True
            producttemplate.account_category = category[0]
            producttemplate.taxes_category = True
            producttemplate.category = category[0]
            if product.id < 0:
                product.code = row['ArtNumber']
                product.name = row['Title']
                product.description = row['Description']
                producttemplate.list_price = Decimal(row['Price'])
                producttemplate.cost_price = Decimal(row['CostPrice'])
                producttemplate.purchasable = True
                producttemplate.saleable = True
                producttemplate.consumable = False
                producttemplate.default_uom = default_uom[0]
                producttemplate.type = 'goods'
                producttemplate.name = row['Title']
                # attributes:
                new_attributes = {}
                for a in attributeset[0].attributes:
                    if a.name == 'color':
                        new_attributes['color'] = row['Color']
                    elif a.name == 'size':
                        new_attributes['size'] = row['Size']
                    elif a.name == 'image':
                        new_attributes['image'] = row['Img180_url']
                    elif a.name == 'image_tn':
                        new_attributes['image_tn'] = row['Img60_url']
                    elif a.name == 'serial_number':
                        new_attributes['serial_number'] = row['ArtNumber']
                    elif a.name == 'pattern':
                        new_attributes['pattern'] = row['Pattern']
                    elif a.name == 'topseller':
                        if row['Topseller'] == 'TRUE':
                            new_attributes['topseller'] = True
                        else:
                            new_attributes['topseller'] = False
                producttemplate.attribute_set = attributeset[0]
                producttemplate.save()
                product.template = producttemplate
                product.attributes = new_attributes
                product.save()
    finally:
        f.close()
