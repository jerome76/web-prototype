from proteus import config, Model, Wizard, Report
import csv
from decimal import *
from flask_shop import app
from datetime import date

DEFAULT_PARTY_SUPPLIER = 'Supplier'


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
                    effective_date = date.strptime(row['stock.move_effective_date'], "%Y-%m-%dT")
                stockmove.effective_date = effective_date
                if row['stock.move_planned_date'] == 'today':
                    planned_date = date.today()
                else:
                    planned_date = date.strptime(row['stock.move_planned_date'], "%Y-%m-%dT")
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
                    try:
                        Subdivision = Model.get('country.subdivision')
                        if countrycode == 'GB':
                            (subdivision,) = Subdivision.find([('name', '=', row['state']), ('country', '=', 13)])
                        else:
                            (subdivision,) = Subdivision.find([('code', 'like', row['country'] + '-' + row['state'] + '%')])
                        party.addresses[0].subdivision = subdivision
                    except ValueError:
                        print ('***** Error: could not find subdivision: ' + row['state'] + ' for country ' +
                               row['country'])
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


def getProductTemplate(producttemplatelist=None, name=None):
    for i in producttemplatelist:
        if name == i.name:
            return i
    return None


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
        Producttemplate = Model.get('product.template')
        producttemplatelist = Producttemplate.find([('id', '>', 0)])
        Product = Model.get('product.product')
        for row in reader:
            print(row['code'], row['name'], row['description'], row['quantity'])
            product = Product()
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
            product.template = getProductTemplate(producttemplatelist, row['product.template_name'])
            product.attributes = new_attributes
            product.save()
    finally:
        f.close()


def getUOM(productUOMList=None, unit=None):
    for i in productUOMList:
        if unit == i.symbol:
            return i
    return None


def getProductCategory(productcategoryList=None, name=None):
    for i in productcategoryList:
        if name == i.name:
            return i
    return None


def getProductAttributeset(productattributesetList=None, name=None):
    for i in productattributesetList:
        if name == i.name:
            return i
    return None


def import_product_template(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for product templates')
        readertest = csv.DictReader(f)
        print(readertest.fieldnames)
        for row in readertest:
            print(row['name'], row['default_uom'], row['consumable'], row['type'], row['attribute_set'],
                  row['taxes_category'], row['accounts_category'], row['account_category'], row['purchasable'],
                  row['purchase_uom'], row['salable'], row['sale_uom'])

        f.seek(0)
        print('Start import')
        reader = csv.DictReader(f)
        ProductUOM = Model.get('product.uom')
        productUOMList = ProductUOM.find([('id', '>', 0)])
        Attributeset = Model.get('product.attribute.set')
        attributesetlist = Attributeset.find([('id', '>', 0)])
        Category = Model.get('product.category')
        categorylist = Category.find([('id', '>', 0)])
        for row in reader:
            print(row['name'], row['default_uom'], row['consumable'], row['type'], row['attribute_set'],
                  row['taxes_category'], row['accounts_category'], row['account_category'], row['purchasable'],
                  row['purchase_uom'], row['salable'], row['sale_uom'])
            ProductTemplate = Model.get('product.template')
            Product = Model.get('product.product')
            duplicate = ProductTemplate.find([('name', '=', row['name'])])
            if duplicate:
                print('Existing product template found: ' + row['name'])
            else:
                producttemplate = ProductTemplate()
                producttemplate.name = row['name']
                producttemplate.default_uom = getUOM(productUOMList, row['default_uom'])
                if row['consumable'] == 'TRUE':
                    producttemplate.consumable = True
                else:
                    producttemplate.consumable = False
                producttemplate.type = row['type']
                producttemplate.attribute_set = getProductAttributeset(attributesetlist, row['attribute_set'])
                if row['taxes_category'] == 'TRUE':
                    producttemplate.taxes_category = True
                else:
                    producttemplate.taxes_category = False
                if row['accounts_category'] == 'TRUE':
                    producttemplate.accounts_category = True
                else:
                    producttemplate.accounts_category = False
                producttemplate.account_category = getProductCategory(categorylist, row['account_category'])
                if row['purchasable'] == 'TRUE':
                    producttemplate.purchasable = True
                else:
                    producttemplate.purchasable = False
                producttemplate.purchase_uom = getUOM(productUOMList, row['purchase_uom'])
                if row['salable'] == 'TRUE':
                    producttemplate.salable = True
                else:
                    producttemplate.salable = False
                producttemplate.sale_uom = getUOM(productUOMList, row['sale_uom'])
                producttemplate.list_price = Decimal(row['list_price'])
                producttemplate.cost_price = Decimal(row['cost_price'])
                producttemplate.save()
                '''product = Product()
                product.code = ''
                product.description = ''
                product.template = producttemplate
                product.save()'''
    finally:
        f.close()


def import_product_attributeset(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for product attributeset')
        readertest = csv.DictReader(f)
        print(readertest.fieldnames)
        for row in readertest:
            print(row['attributeset_name'], row['digits'], row['selection'], row['name'], row['string'], row['type_'],
                  row['selection_sorted'])

        f.seek(0)
        print('Start import')
        reader = csv.DictReader(f)
        for row in reader:
            print(row['attributeset_name'], row['digits'], row['selection'], row['name'], row['string'], row['type_'],
                  row['selection_sorted'])
            Attributeset = Model.get('product.attribute.set')
            attributesetlist = Attributeset.find([('name', '=', row['attributeset_name'])])
            if attributesetlist:
                attributeset = attributesetlist[0]
            else:
                attributeset = Attributeset()
                attributeset.name = row['attributeset_name']
                attributeset.save()
            Attribute = Model.get('product.attribute')
            duplicate = Attribute.find([('name', '=', row['name'])])
            if duplicate:
                print('Existing attribute found: ' + row['name'])
            else:
                attribute = attributeset.attributes.new()
                attribute.digits = int(row['digits'])
                attribute.selection = row['selection']
                attribute.name = row['name']
                attribute.string = row['string']
                attribute.type_ = row['type_']
                if row['selection_sorted'] == 'TRUE':
                    attribute.selection_sorted = True
                else:
                    attribute.selection_sorted = False
                attributeset.save()
    finally:
        f.close()


def import_product_categories(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for categories')
        readertest = csv.DictReader(f)
        print(readertest.fieldnames)
        for row in readertest:
            print(row['name'], row['parent'], row['accounting'], row['taxes_parent'], row['account_parent'])

        f.seek(0)
        print('Start import')
        reader = csv.DictReader(f)
        for row in reader:
            print(row['name'], row['parent'], row['accounting'], row['taxes_parent'], row['account_parent'])
            Category = Model.get('product.category')
            duplicate = Category.find([('name', '=', row['name'])])
            if duplicate:
                print('Existing category found: ' + row['name'])
            else:
                category = Category()
                category.name = row['name']
                if row['accounting'] == 'TRUE':
                    category.accounting = True
                else:
                    category.accounting = False
                if row['taxes_parent'] == 'TRUE':
                    category.taxes_parent = True
                else:
                    category.taxes_parent = False
                if row['account_parent'] == 'TRUE':
                    category.account_parent = True
                else:
                    category.account_parent = False
                if row['parent'] != '':
                    parent = Category.find([('name', '=', row['parent'])])
                    if parent:
                        category.parent = parent[0]
                category.save()
    finally:
        f.close()


def getLocation(locationlist, code):
    for i in locationlist:
        if code == i.code:
            return i
    return None


def import_shipment_in(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
        print('Testing csv file structure for product supplier shipment')
        readertest = csv.DictReader(f)
        print(readertest.fieldnames)
        for row in readertest:
            print(row['code'], row['name'], row['description'], row['quantity'], row['product.template_name'],
                  row['stock.location_warehouse'], row['stock.location_from'], row['stock.location_to'],
                  row['stock.move_effective_date'], row['stock.move_planned_date'], row['stock.move_unit_price'],
                  row['stock.move_cost_price'], row['supplier'])

        f.seek(0)
        print('Start import')
        StockShipmentIn = Model.get('stock.shipment.in')
        duplicate = StockShipmentIn.find([('reference', '=', filename)])
        if duplicate:
            print('Existing supplier shipment found: ' + str(duplicate[0].id) + ' - ' + filename)
            raise ValueError('Existing supplier shipment found with the same filename: ' + str(duplicate[0].id) + ' - '
                             + filename)
        else:
            stockshipmentin = StockShipmentIn()
            stockshipmentin.reference = filename
            Location = Model.get('stock.location')
            locationlist = Location.find([('id', '>', 0)])
            Party = Model.get('party.party')
            supplier = Party.find([('name', '=', DEFAULT_PARTY_SUPPLIER)], limit=1)
            PartyAddress = Model.get('party.address')
            supplier_address = PartyAddress.find([('party', '=', supplier[0].id)], limit=1)
            if row['stock.move_planned_date'] == 'today':
                planned_date = date.today()
            else:
                planned_date = date.strptime(row['stock.move_planned_date'], "%Y-%m-%dT")
            stockshipmentin.planned_date = planned_date
            if row['stock.move_effective_date'] == 'today':
                effective_date = date.today()
            else:
                effective_date = date.strptime(row['stock.move_effective_date'], "%Y-%m-%dT")
            stockshipmentin.effective_date = effective_date
            stockshipmentin.supplier = supplier[0]
            stockshipmentin.contact_address = supplier_address[0]
            stockshipmentin.warehouse = getLocation(locationlist, row['stock.location_warehouse'])
            stockshipmentin.save()
            ProductUOM = Model.get('product.uom')
            productUOMList = ProductUOM.find([('id', '>', 0)])
            reader = csv.DictReader(f)
            moves = []
            if stockshipmentin.id > 0:
                StockInventoryLine = Model.get('stock.inventory.line')
                stockinventoryline = StockInventoryLine()
                for row in reader:
                    print(row['code'], row['name'], row['description'], row['quantity'], row['product.template_name'])
                    # internal SUP -> IN
                    stockmove = stockinventoryline.moves.new()
                    stockmove.shipment = stockshipmentin
                    Product = Model.get('product.product')
                    product = Product.find([('code', '=', row['code'])])
                    stockmove.product = product[0]
                    stockmove.quantity = Decimal(row['quantity'])
                    stockmove.uom = getUOM(productUOMList, row['stock.move_uom'])
                    stockmove.from_location = getLocation(locationlist, 'SUP')
                    stockmove.to_location = getLocation(locationlist, row['stock.location_from'])
                    stockmove.planned_date = planned_date
                    stockmove.effective_date = effective_date
                    stockmove.unit_price = Decimal(row['stock.move_unit_price'])
                    if row['stock.move_cost_price'] == 'default':
                        stockmove.cost_price = product[0].cost_price
                    else:
                        stockmove.cost_price = Decimal(row['stock.move_cost_price'])
                    stockmove.save()
                    moves.append(stockmove)
    finally:
        f.close()
