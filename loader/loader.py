import csv
import sys
from proteus import config, Model, Wizard, Report
from decimal import *
import urllib, cStringIO
from PIL import Image
import StringIO
from datetime import date

CONFIG = "../tryton.conf"
DATABASE_NAME = "tryton_dev"


def loadCustomers():
    f = open(sys.argv[2], 'rb')
    countrycode = sys.argv[3]
    if countrycode is None:
        print "Please provide a country code. e.g. 'CH'"
    try:
        reader = csv.DictReader(f)
        Lang = Model.get('ir.lang')
        (en,) = Lang.find([('code', '=', 'en_US')])
        Country = Model.get('country.country')
        (ch, ) = Country.find([('code', '=', countrycode)])
        for row in reader:
            print(row['first_name'], row['last_name'], row['company_name'])
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
                party.addresses[0].country = ch
                # party.addresses[0].subdivision = row['state']
                party.addresses[0].invoice = True
                party.addresses[0].delivery = True
                party.save()
    finally:
        f.close()

def loadProducts():
    f = open(sys.argv[2], 'rb')
    csvlisttype = sys.argv[3]
    if csvlisttype is None:
        print "Please provide a listtype 'A' or 'B'"
    try:
        Default_uom = Model.get('product.uom')
        default_uom = Default_uom.find([('symbol', '=', 'u')])
        Category = Model.get('product.category')
        category = Category.find([('name', '=', 'Cosy')])
        Attributeset = Model.get('product.attribute.set')
        attributeset = Attributeset.find([('name', '=', 'default_webshop')])
        reader = csv.DictReader(f)
        if csvlisttype == 'A':
            for row in reader:
                print(row['Price'], row['Shipping'], row['Manufacturer'])
                Product = Model.get('product.product')
                product = Product()
                Producttemplate = Model.get('product.template')
                producttemplate = Producttemplate()
                producttemplate.accounts_category = True
                producttemplate.account_category = category[0]
                producttemplate.taxes_category = True
                producttemplate.category = category[0]
                if product.id < 0:
                    product.code = row['ArtNumber']
                    product.name = row['Title']
                    product.description = row['Description_Short']
                    producttemplate.list_price = Decimal(row['Price'])
                    producttemplate.cost_price = Decimal(row['Price'])
                    producttemplate.purchasable = True
                    producttemplate.saleable = True
                    producttemplate.consumable = False
                    producttemplate.default_uom = default_uom[0]
                    producttemplate.type = 'goods'
                    producttemplate.name = row['Title']
                    producttemplate.save()
                    # product.product_template = producttemplate
                    product.template = producttemplate
                    product.save()
        elif csvlisttype == 'B':
            for row in reader:
                print(row['Price'], row['Name'], row['MerchantCategory'])
                Product = Model.get('product.product')
                product = Product()
                Producttemplate = Model.get('product.template')
                producttemplate = Producttemplate()
                producttemplate.accounts_category = True
                producttemplate.account_category = category[0]
                producttemplate.taxes_category = True
                producttemplate.category = category[0]
                if product.id < 0:
                    product.code = row['SKU']
                    product.name = row['Name']
                    product.description = row['Description']
                    producttemplate.list_price = Decimal(row['Price'])
                    producttemplate.cost_price = Decimal(row['Price'])
                    producttemplate.purchasable = True
                    producttemplate.saleable = True
                    producttemplate.consumable = False
                    producttemplate.default_uom = default_uom[0]
                    producttemplate.type = 'goods'
                    producttemplate.name = row['Name']
                    # producttemplate.save()
                    # product.product_template = producttemplate
                    product.template = producttemplate
                    product.save()
        if csvlisttype == 'C':
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
                        elif a.name == 'available':
                            if row['Available'] == 'TRUE':
                                new_attributes['available'] = True
                            else:
                                new_attributes['available'] = False
                    producttemplate.attribute_set = attributeset[0]
                    producttemplate.save()
                    product.template = producttemplate
                    product.attributes = new_attributes
                    # product.product_template = producttemplate
                    #Attribute = Model.get('product.attribute')
                    #attribute = Attribute.find([('name', '=', 'size')])
                    #attribute[0].selection = 'l'
                    #product.attributes = {attribute[0].name: attribute[0].selection}
                    product.save()

    finally:
        f.close()

def loadImages():
    f = open(sys.argv[2], 'rb')
    csvlisttype = sys.argv[3]
    if csvlisttype is None:
        print "Please provide a listtype 'A' or 'B'"
    try:
        reader = csv.DictReader(f)
        if csvlisttype == 'A':
            for row in reader:
                print(row['ArtNumber'], row['Img180_url'], row['Img60_url'])
                if (row['Img180_url'] == ''):
                    continue
                # image 180px
                imagefile = cStringIO.StringIO(urllib.urlopen(row['Img180_url']).read())
                img = Image.open(imagefile)
                output = StringIO.StringIO()
                img.save(output, format="PNG")
                pngcontents = output.getvalue()
                output.close()
                with open('images180/'+row['ArtNumber']+'.png', 'wb') as imgfile:
                    imgfile.write(pngcontents)
                    imgfile.close()
                    imagefile.close()
                # image 60px
                # image 180px
                imagefile = cStringIO.StringIO(urllib.urlopen(row['Img60_url']).read())
                img = Image.open(imagefile)
                output = StringIO.StringIO()
                img.save(output, format="PNG")
                pngcontents = output.getvalue()
                output.close()
                with open('images60/'+row['ArtNumber']+'.png', 'wb') as imgfile:
                    imgfile.write(pngcontents)
                    imgfile.close()
                    imagefile.close()
        if csvlisttype == 'B':
            for row in reader:
                print(row['SKU'], row['URL to Image'], row['URL to thumbnail image'])
                if (row['URL to Image'] == ''):
                    continue
                # image 180px
                imagefile = cStringIO.StringIO(urllib.urlopen(row['URL to Image']).read())
                img = Image.open(imagefile)
                output = StringIO.StringIO()
                img.save(output, format="PNG")
                pngcontents = output.getvalue()
                output.close()
                with open('images/'+row['SKU']+'.png', 'wb') as imgfile:
                    imgfile.write(pngcontents)
                    imgfile.close()
                    imagefile.close()
                # image 60px
                # image 180px
                imagefile = cStringIO.StringIO(urllib.urlopen(row['URL to thumbnail image']).read())
                img = Image.open(imagefile)
                output = StringIO.StringIO()
                img.save(output, format="PNG")
                pngcontents = output.getvalue()
                output.close()
                with open('images/tn/'+row['SKU']+'.png', 'wb') as imgfile:
                    imgfile.write(pngcontents)
                    imgfile.close()
                    imagefile.close()
    finally:
        f.close()


def loadInternalShipment():
    f = open(sys.argv[2], 'rb')
    csvlisttype = sys.argv[3]
    if csvlisttype is None:
        print "Please provide a listtype 'A' or 'B'"
    try:
        StockShipmentInternal = Model.get('stock.shipment.internal')
        stockshipmentinternal = StockShipmentInternal()
        stockshipmentinternal.reference = sys.argv[2]
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



def main():
    config.set_trytond(DATABASE_NAME, config_file=CONFIG)
    trytontype = sys.argv[1]
    f = open(sys.argv[2], 'rb')
    if trytontype is None:
        print "Please provide a type to load"
    elif trytontype == 'customer':
        loadCustomers()
    elif trytontype == 'product':
        loadProducts()
    elif trytontype == 'image':
        loadImages()
    elif trytontype == 'shipment':
        loadInternalShipment()


if __name__ == '__main__':
    main()