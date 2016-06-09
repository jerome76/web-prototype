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
            print(row['code'], row['name'], row['description'], row['quantity'], row['product.template_name'],
                  row['stock.location_from'], row['stock.location_to'], row['stock.move_effective_date'],
                  row['stock.move_planned_date'], row['stock.move_unit_price'], row['stock.move_cost_price'])
        f.seek(0)
        print('Start import')
        StockShipmentInternal = Model.get('stock.shipment.internal')
        stockshipmentinternal = StockShipmentInternal()
        stockshipmentinternal.reference = filename
        LocationFrom = Model.get('stock.location')
        locationfrom = LocationFrom.find([('code', '=', row['stock.location_from'])])
        stockshipmentinternal.from_location = locationfrom[0]
        LocationTo = Model.get('stock.location')
        locationto = LocationTo.find([('code', '=', row['stock.location_to'])])
        stockshipmentinternal.to_location = locationto[0]
        stockshipmentinternal.effective_date = date.today()
        stockshipmentinternal.planned_date = date.today()
        stockshipmentinternal.save()
        reader = csv.DictReader(f)
        moves = []
        if stockshipmentinternal.id > 0:
            for row in reader:
                print(row['code'], row['name'], row['description'], row['quantity'], row['stock.location_from'],
                      row['stock.location_to'])
                StockMove = Model.get('stock.move')
                stockmove = StockMove()
                stockmove.shipment = stockshipmentinternal
                Product = Model.get('product.product')
                product = Product.find([('code', '=', row['code'])])
                stockmove.product = product[0]
                stockmove.quantity = int(row['quantity'])
                stockmove.from_location = locationfrom[0]
                stockmove.to_location = locationto[0]
                if row['stock.move_effective_date'] == 'today':
                    effective_date = date.today()
                else:
                    effective_date = date.strptime("2012-10-09", "%Y-%m-%dT")
                stockmove.effective_date = effective_date
                if row['stock.move_planned_date'] == 'today':
                    planned_date = date.today()
                else:
                    planned_date = date.strptime("2012-10-09", "%Y-%m-%dT")
                stockmove.planned_date = planned_date
                stockmove.unit_price = Decimal(row['stock.move_unit_price'])
                if row['stock.move_cost_price'] == 'default':
                    stockmove.cost_price = product[0].cost_price
                else:
                    stockmove.cost_price = Decimal(row['stock.move_cost_price'])
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
            print(row['first_name'], row['last_name'], row['company_name'], row['address'], row['city'], row['country'],
                  row['state'], row['zip'], row['phone'], row['mobile'], row['email'], row['website'])

        f.seek(0)
        print('Start import')
        reader = csv.DictReader(f)
        for row in reader:
            countrycode = row['country']
            Lang = Model.get('ir.lang')
            (en,) = Lang.find([('code', '=', 'en_US')])
            Country = Model.get('country.country')
            (cc,) = Country.find([('code', '=', countrycode)])
            print(row['first_name'], row['last_name'], row['company_name'], row['address'], row['city'], row['country'],
                  row['state'], row['zip'])
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
                if row['state'] is not None:
                    Subdivision = Model.get('country.subdivision')
                    if countrycode == 'GB':
                        (subdivision,) = Subdivision.find([('name', '=', row['state']), ('country', '=', 13)])
                    else:
                        (subdivision,) = Subdivision.find([('code', 'like', row['country'] + '-' + row['state'] + '%')])
                    party.addresses[0].subdivision = subdivision
                if row['invoice'] == 'TRUE':
                    party.addresses[0].invoice = True
                else:
                    party.addresses[0].invoice = False
                if row['delivery'] == 'TRUE':
                    party.addresses[0].delivery = True
                else:
                    party.addresses[0].delivery = False
                party.addresses[0]
                party.save()
                # Contact
                contactmechanismlist = []
                if row['phone'] is not None:
                    ContactMechanism = Model.get('party.contact_mechanism')
                    contactmechanism = ContactMechanism()
                    contactmechanism.party = party
                    contactmechanism.type = 'phone'
                    contactmechanism.value = row['phone']
                    contactmechanismlist.append(contactmechanism)
                    contactmechanism.save()
                if row['mobile'] is not None:
                    ContactMechanism = Model.get('party.contact_mechanism')
                    contactmechanism = ContactMechanism()
                    contactmechanism.party = party
                    contactmechanism.type = 'mobile'
                    contactmechanism.value = row['mobile']
                    contactmechanismlist.append(contactmechanism)
                    contactmechanism.save()
                if row['email'] is not None:
                    ContactMechanism = Model.get('party.contact_mechanism')
                    contactmechanism = ContactMechanism()
                    contactmechanism.party = party
                    contactmechanism.type = 'email'
                    contactmechanism.value = row['email']
                    contactmechanismlist.append(contactmechanism)
                    contactmechanism.save()
                if row['website'] is not None:
                    ContactMechanism = Model.get('party.contact_mechanism')
                    contactmechanism = ContactMechanism()
                    contactmechanism.party = party
                    contactmechanism.type = 'website'
                    contactmechanism.value = row['website']
                    contactmechanism.save()
                    contactmechanismlist.append(contactmechanism)
                party.contact_mechanism = contactmechanismlist
    finally:
        f.close()


def import_products(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for products')
        readertest = csv.DictReader(f)
        print(readertest.fieldnames)
        for row in readertest:
            print(row['code'], row['name'], row['description'], row['quantity'], row['product.template_name'])

        f.seek(0)
        print('Start import')
        reader = csv.DictReader(f)
        for row in reader:
            print(row['code'], row['name'], row['description'], row['quantity'])
            Product = Model.get('product.product')
            product = Product()
            Producttemplate = Model.get('product.template')
            producttemplatelist = Producttemplate.find([('name', '=', row['product.template_name'])])
            if producttemplatelist is None:
                raise KeyError('No product.template found for ' + row['product.template_name'])
            else:
                producttemplate = producttemplatelist[0]
            if product.id < 0:
                product.code = row['code']
                product.name = row['name']
                product.description = row['description']
                # attributes:
                new_attributes = {}
                for fieldname in reader.fieldnames:
                    if fieldname[0:10] == 'attribute_':
                        if row[fieldname] == 'TRUE':
                            new_attributes[fieldname[10:]] = True
                        elif row[fieldname] == 'FALSE':
                            new_attributes[fieldname[10:]] = False
                        else:
                            new_attributes[fieldname[10:]] = row[fieldname]
                product.template = producttemplate
                product.attributes = new_attributes
                product.save()
    finally:
        f.close()
