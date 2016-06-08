from proteus import config, Model, Wizard, Report
import csv
from decimal import *
from flask_shop import app


def import_products(filename):
    f = open(filename, 'rb')
    config.set_trytond(app.config['TRYTON_DATABASE_NAME'], config_file=app.config['TRYTON_CONFIG_FILE'])
    try:
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
