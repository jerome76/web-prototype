import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.uix.button import Button
from kivy.config import Config, ConfigParser
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import ScreenManager, Screen
import json
from kivy.clock import Clock
from decimal import Decimal, InvalidOperation
from kivy.factory import Factory
from kivy.uix.popup import Popup
import os, os.path
import glob, urllib2
import traceback
from functools import partial
import sys
from PIL import Image, ImageDraw, ImageFont

TRYTON_HOST = "http://192.168.1.102:5000/pos/products"
TRYTON_HOST_SEARCH = "http://192.168.1.102:5000/pos/product/"


class ImageButton(ButtonBehavior, kivy.uix.image.Image):
    pb = ProgressBar(max=100) #100
    popup = Popup(title='Uploading payslips',
                  content=pb,
                  size_hint=(0.7, 0.3))

    def on_release(self):
        print ('POSScreen.ImageButton.on_press: upload payslips')
        upload_count = len(glob.glob('offline/*.json'))
        if upload_count > 0:
            self.popup.open()
            self.pb.value = 0
            file_count = len(glob.glob('offline/*.json'))
            increment = 100.0/file_count + 1
            for fn in glob.glob('offline/*.json'):
                if os.path.isfile(fn):
                    Clock.schedule_once(partial(self.upload_payslips, fn, increment), 0)
        config = ConfigParser.get_configparser(name='app')
        if config.get('section1', 'download_images_after_sync') == 'True':
            self.parent.parent.parent.load_all_images()

    def upload_payslips(self, fn, pb_inc, *args):
        def on_success(req, result):
            self.pb.value += pb_inc
            print("Progressbar is on {0}%".format(self.pb.value))
            try:
                os.remove(fn)
            except OSError:
                print(traceback.format_exc())
                print "POSScreen.upload_payslips() on_success: no such file or directory"
            if self.pb.value >= 99.9:
                self.popup.dismiss()
                self.parent.parent.parent.update_icon(True)

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            self.pb.value += pb_inc
            print("Progressbar is on {0}%".format(self.pb.value))
            if self.pb.value >= 99.9:
                self.popup.dismiss()
                self.parent.parent.parent.update_icon(False)

        try:
            print ("POSScreen.upload_payslips()" + fn + ' ' + str(pb_inc))
            config = ConfigParser.get_configparser(name='app')
            print(config.get('serverconnection', 'server.url'))
            saleurl = config.get('serverconnection', 'server.url') + "pos/sale/"
            with open(fn) as data_file:
                result = json.load(data_file)
                file_param = dict([])
                file_param['filename'] = fn
                result['filename'] = file_param
                data_json = json.dumps(result)
                headers = {'Content-type': 'application/jsonrequest', 'Accept': 'application/jsonrequest'}
                UrlRequest(url=saleurl, on_success=on_success, on_failure=on_failure, on_error=on_error,
                           req_headers=headers, req_body=data_json)
        except Exception:
            print(traceback.format_exc())
            print "POSScreen.upload_payslips() Error: Could not upload payslip"


class DataItem(object):
    qty = Decimal(0.00)
    discount = Decimal(0.00)
    price = Decimal(0.00)
    product_id = None

    def __init__(self, product_id, text='', is_selected=False, qty=Decimal(1.00), discount=Decimal(0.00), price=Decimal(0.00)):
        self.text = text
        self.is_selected = is_selected
        self.qty = qty
        self.discount = discount
        self.price = price
        self.product_id = product_id


class POSScreen(Screen):
    '''Create a controller that receives a custom widget from the kv lang file.

    Add an action to be called from the kv lang file.
    '''
    _selected_line_index = 0
    _mode = 'Qty'
    _current_value = 0.0
    label_wid = ObjectProperty()
    label_total_wid = ObjectProperty()
    icon_wid = ObjectProperty()
    info = StringProperty()
    default_currency = 'CHF'
    products_list = []
    products_search_list = []
    products_json = []
    categories_list = []
    categories_json = []
    currencies_list = []
    currencies_json = []
    customers_list = []
    customers_json = []
    sale_json = []
    customer_id = 0
    customer_name = ''
    order_id = 0
    payslip_items_list = []
    my_data_view = ListProperty([])
    selected_value = StringProperty('select a product.')
    username = ''

    def __init__(self, **kwargs):
        super(Screen,self).__init__(**kwargs)
        self.info = ''
        Clock.schedule_once(self.post_init, 0)

    def post_init(self, *args):
        config = ConfigParser.get_configparser(name='app')
        self.customer_id = config.get('section1', 'default_customer_id')
        self.order_id = int(config.get('section1', 'default_order_id'))
        with open('customers.json') as data_file:
            result = json.load(data_file)
            self.customers_json = result
        for c in result['result']:
            self.customers_list.append(c)
        customer = self.get_customer(self.customer_id)
        if customer:
            self.customer_name = customer["name"]
        else:
            self.customer_name = '???'
        self.btn_customer_wid.text = 'Client: ' + self.customer_name
        print ('post_init...')

    def on_pre_enter(self, *args):
        def on_success(req, result):
            self.update_icon(True)
            with open('products.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            self.products_json = result
            print ('products loaded.')

            if len(result['result']) > 0:
                self.my_tabbed_panel_wid.grid_layout_home_wid.clear_widgets()
            for p in result['result']:
                p_id = str(p['id'])
                if p['code'] is None or p['code'] == '':
                    subtext = p['name']
                else:
                    subtext = p['code']
                image_source = self.get_local_image(p)
                btn = Factory.CustomButton(image_source=image_source, id=p_id,
                                           size_hint_y=None, width=300, height=100, subtext=subtext)
                btn.bind(on_press=self.do_add_item)
                self.products_list.append(btn)
                print ('add online product ' + str(p['id']))
                self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
            self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*dp(110)

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            self.update_icon(False)
            for key, val in self.ids.items():
                print("key={0}, val={1}".format(key, val))
            if len(self.products_list) > 0:
                for n in self.products_list:
                    self.my_tabbed_panel_wid.grid_layout_home_wid.remove_widget(n)
            if len(self.products_list) == 0:
                with open('products.json') as data_file:
                    result = json.load(data_file)
                    self.products_json = result
                for p in result['result']:
                    p_id = str(p['id'])
                    if p['code'] is None or p['code'] == '':
                        subtext = p['name']
                    else:
                        subtext = p['code']
                    image_source = self.get_local_image(p)
                    btn = Factory.CustomButton(image_source=image_source, id=p_id,
                                               size_hint_y=None, width=300, height=100, subtext=subtext)
                    btn.bind(on_press=self.do_add_item)
                    self.products_list.append(btn)
                    print ('add local product ' + str(p['id']))
                    self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
                self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*110

        def getTabHeader(tablist=None, name=''):
            for t in tablist:
                if t.text == name:
                    return True
            return False

        def on_success_categories(req, result):
            with open('categories.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            self.categories_json = result
            print ('categories loaded.')
            for i in result['result']:
                name = i['name']
                self.categories_list.append(i)
                if not getTabHeader(self.my_tabbed_panel_wid.tab_list, name):
                    th = TabbedPanelHeader(text=name)
                    self.my_tabbed_panel_wid.add_widget(th)
                    layout = GridLayout(cols=4, spacing=2, size_hint_y=None)
                    layout.bind(minimum_height=layout.setter('height'))
                    root = ScrollView()
                    root.add_widget(layout)
                    th.content = root
                print ('add online category ' + name)

        def on_failure_categories(req, result):
            on_error_categories(req, result)

        def on_error_categories(req, result):
            self.update_icon(False)
            print 'could not load categories'
            try:
                with open('categories.json') as data_file:
                    result = json.load(data_file)
                    self.categories_json = result
                for i in result['result']:
                    name = i['name']
                    self.categories_list.append(i)
                    if not getTabHeader(self.my_tabbed_panel_wid.tab_list, name):
                        th = TabbedPanelHeader(text=name)
                        self.my_tabbed_panel_wid.add_widget(th)
                        layout = GridLayout(cols=4, spacing=2, size_hint_y=None)
                        layout.bind(minimum_height=layout.setter('height'))
                        root = ScrollView()
                        root.add_widget(layout)
                        th.content = root
                        print ('add local category ' + name)
            except:
                traceback.print_exc(file=sys.stdout)

        def on_success_currencies(req, result):
            with open('currencies.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            self.currencies_json = result
            print ('currencies loaded.')
            for i in result['result']:
                rate = Decimal(i['rate'])
                if rate == Decimal(1.000):
                    self.default_currency = i['code']
                    print ('set default currency ' + i['code'])
                if rate > Decimal(0.00000):
                    self.currencies_list.append(i)
                    print ('add currency ' + i['code'])

        def on_failure_currencies(req, result):
            on_error_currencies(req, result)

        def on_error_currencies(req, result):
            self.update_icon(False)
            print 'could not load currencies'
            try:
                with open('currencies.json') as data_file:
                    result = json.load(data_file)
                    self.currencies_json = result
                for i in result['result']:
                    rate = Decimal(i['rate'])
                    if rate == Decimal(1.000):
                        self.default_currency = i['code']
                        print ('set default currency ' + i['code'])
                    if i['rate'] > Decimal(0.00000):
                        self.currencies_list.append(i)
            except:
                traceback.print_exc(file=sys.stdout)
        try:
            self.btn_order_id_wid.text = str(self.order_id)
            self.username = self.manager.get_screen('main').textinput_user_wid.text
            config = ConfigParser.get_configparser(name='app')
            print(config.get('serverconnection', 'server.url'))
            hideoutofstockitems = config.get('section1', 'hide_out_of_stock_items')
            producturl = config.get('serverconnection', 'server.url') + "pos/products/" + hideoutofstockitems
            if len(self.products_list) == 0:
                UrlRequest(url=producturl, on_success=on_success, on_failure=on_failure, on_error=on_error)
            categoryurl = config.get('serverconnection', 'server.url') + "pos/categories/"
            if len(self.categories_list) == 0:
                UrlRequest(url=categoryurl, on_success=on_success_categories, on_failure=on_failure_categories,
                           on_error=on_error_categories)
            currencyurl = config.get('serverconnection', 'server.url') + "pos/currency/"
            if len(self.currencies_list) == 0:
                UrlRequest(url=currencyurl, on_success=on_success_currencies, on_failure=on_failure_currencies,
                       on_error=on_error_currencies)

        except:
            traceback.print_exc(file=sys.stdout)
        print "Initialize products selection"

    def update_icon(self, online=True):
        offline = '_offline'
        if online:
            offline = ''
        self.icon_wid.source = 'data/icon' + offline + '.png'
        try:
            upload_count = len(glob.glob('offline/*.json'))
            if upload_count > 0:
                img = Image.open('data/icon' + offline + '.png')
                draw = ImageDraw.Draw(img)
                draw.ellipse((50, 65, 95, 95), fill=(165, 208, 101, 0))
                font = ImageFont.truetype("data/verdanab.ttf", 24)
                posx = 65
                if upload_count > 9:
                    posx = 55
                draw.text((posx, 65), str(upload_count), (255, 255, 255), font=font)
                img.save('data/icon2' + offline + '.png')
                self.icon_wid.source = 'data/icon2' + offline + '.png'
                self.icon_wid.reload()
        except:
            traceback.print_exc(file=sys.stdout)

    @staticmethod
    def format_currency_amount(amount):
        return '{:20,.2f}'.format(amount)

    def load_all_images(self):
        config = ConfigParser.get_configparser(name='app')
        for p in self.products_json['result']:
            image_name = p['code']
            if p['code'] is None:
                image_name = str(p['id'])
            image_file = image_name + "-small.png"
            self.download_photo(config.get('serverconnection', 'server.url') + "static/products/" + image_file,
                                "./products/" + image_file)

    def download_photo(self, img_url, file_path):
        try:
            response = urllib2.urlopen(img_url)
            content = response.read()
            downloaded_image = file(file_path, "wb")
            downloaded_image.write(content)
            downloaded_image.close()
        except urllib2.HTTPError, urllib2.URLError:
            print('File not found ' + img_url)

    def do_search(self):
        def on_success(req, result):
            print ('search success.')
            for p in result['result']:
                p_id = str(p['id'])
                if p['code'] is None or p['code'] == '':
                    subtext = p['name']
                else:
                    subtext = p['code']
                image_source = self.get_local_image(p)
                btn = Factory.CustomButton(image_source=image_source, id=p_id,
                                           size_hint_y=None, width=300, height=100, subtext=subtext)
                btn.bind(on_press=self.do_add_item)
                self.products_search_list.append(btn)
                self.my_tabbed_panel_wid.grid_layout_search_wid.add_widget(btn)
                self.my_tabbed_panel_wid.switch_to(self.my_tabbed_panel_wid.tab_search_wid)
            self.my_tabbed_panel_wid.grid_layout_search_wid.height = (len(result['result'])/4+4)*110
            self.text_input_wid.text = ''

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            print ('POSScrean.search().on_error() ')

        print ('POSScreen.do_search():')
        if len(self.products_search_list) > 0:
            for n in self.products_search_list:
                self.my_tabbed_panel_wid.grid_layout_search_wid.remove_widget(n)
        self.products_search_list = []
        config = ConfigParser.get_configparser(name='app')
        producturl = config.get('serverconnection', 'server.url') + "pos/product/" + self.text_input_wid.text
        UrlRequest(producturl, on_success=on_success, on_failure=on_failure, on_error=on_error)

    def do_category(self, category):
        print('do_category: ' + category)
        if category == 'Home':
            self.my_tabbed_panel_wid.grid_layout_home_wid.clear_widgets()
            with open('products.json') as data_file:
                result = json.load(data_file)
                self.products_json = result
            for p in result['result']:
                p_id = str(p['id'])
                if p['code'] is None or p['code'] == '':
                    subtext = p['name']
                else:
                    subtext = p['code']
                image_source = self.get_local_image(p)
                btn = Factory.CustomButton(image_source=image_source, id=p_id,
                                           size_hint_y=None, width=300, height=100, subtext=subtext)
                btn.bind(on_press=self.do_add_item)
                self.products_list.append(btn)
                print ('add local product ' + str(p['id']))
                self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
            self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*110

    def get_product(self, p_id):
        for i in self.products_json['result']:
            current_id = str(i['id'])
            if current_id == p_id:
                return i
        return

    def get_customer(self, c_id):
        for i in self.customers_json['result']:
            current_id = str(i['id'])
            if current_id == c_id:
                return i
        return

    @staticmethod
    def get_local_image(product):
        image_name = product['code']
        if product['code'] is None:
            image_name = product['id']
        image_source = './products/' + str(image_name) + '-small.png'
        if os.path.isfile(image_source):
            return image_source
        else:
            return './products/null-small.png'

    def do_clear_item_list(self):
        print('do_clear_item_list')
        del self.my_data_view[:]
        self._selected_line_index = 0
        self.list_view_wid.height = self.height * 0.6
        self.btn_order_id_wid.text = str(self.order_id)

    def do_add_item(self, event):
        print('Add product button <%s> state is <%s>' % (self, event))
        product = self.get_product(event.id)
        if product is not None:
            newitem = DataItem(event.id, text="[" + str(product['id']) + '-' + str(product['code']) + "] " + product['name']
                                    + ' '
                                    + self.format_currency_amount(Decimal(product['price']) * Decimal(1.000))
                                    + ' ' + self.default_currency + "\n"
                                    + '   1 ' + product['uom_symbol'] + ' at ' + product['price']
                                    + ' ' + self.default_currency
                                    + " / " + product['uom_symbol'],
                               price=Decimal(product['price']),
                               qty=Decimal(1.000))
            newitem.color = (0.1,0.1,0.1,1)
        else:
            newitem = DataItem(event.id, text=str(event.id))
            newitem.color = (0.1, 0.1, 0.1, 1)
        print('do_add_item ' + newitem.text)
        self.my_data_view.append(newitem)
        if hasattr(self.list_view_wid, '_reset_spopulate'):
            self.list_view_wid._reset_spopulate()
        self._selected_line_index = self.list_view_wid.adapter.get_count()
        if self._selected_line_index > 0:
            adapter = self.list_view_wid.adapter
            view = adapter.get_view(self._selected_line_index-1)
            adapter.handle_selection(view, True)
            view.trigger_action(duration=0)
        # self.list_view_wid.adapter.set_data_item_selection(newitem, True)
        print('do_add_item finished.')

    def selection_change(self, change):
        print('_selected_line_index: ', self._selected_line_index)
        print("selection_change: " + change.text + " " + str(change.is_selected))
        change.background_color = [1, 1, 1, 1]
        self.selected_value = '{}'.format(change.text)
        self.label_total_wid.text = 'Total: ' + self.format_currency_amount(self.get_total())


    def update_qty_disc_price(self, product_id, quantity, discount, price):
        if self.list_view_wid.adapter.get_count() > 0:
            self.my_data_view[self._selected_line_index-1].qty = Decimal(round(quantity))
            product = self.get_product(product_id)
            text = self.get_line(product, Decimal(round(quantity)), discount, price)
            self.my_data_view[self._selected_line_index-1].text = text
            if hasattr(self.list_view_wid, '_reset_spopulate'):
                self.list_view_wid.adapter.data.prop.dispatch(self.list_view_wid.adapter.data.obj())
            view = self.list_view_wid.adapter.get_view(self._selected_line_index-1)
            view.trigger_action(duration=0)

    def set_mode(self, mode):
        self._mode = mode
        self.info = ''

    def get_line(self, product, quantity, discount, price):
        return "[" + str(product['id']) + '-' + str(product['code']) + "] " + product['name'] \
               + ' ' \
               + self.format_currency_amount(price * quantity) + ' ' + self.default_currency + "\n"  \
               + ' ' + str(quantity) + ' ' + product['uom_symbol'] + ' at ' + self.format_currency_amount(price) \
               + ' ' + self.default_currency + " / " + product['uom_symbol'] \
               + ' ' + str(discount)

    def get_total(self):
        total = Decimal(0.000)
        for v in self.my_data_view:
            total += v.qty * v.price
        return total

    def do_action(self, event):
        print('POSScreen Button ' + str(event) + ' clicked.')
        do_update_line = False
        if self._selected_line_index == 0:
            return
        active_line = self.my_data_view[self._selected_line_index-1]
        product_id = active_line.product_id
        if type(event) is int:
            do_update_line = True
            if len(self.my_data_view) > 0:
                self.info += str(event)
        elif type(event) is str:
            if len(self.my_data_view) > 0:
                if event == '+/-':
                    do_update_line = True
                    if self.info.startswith('-'):
                        self.info = self.info[1:]
                    else:
                        if len(self.info) > 0:
                            self.info = '-' + self.info
                        else:
                            self.info = '0'
                elif event == '.':
                    if '.' not in self.info:
                        if len(self.info) > 0:
                            self.info += '.'
                        else:
                            self.info = '0.'

            if event == 'Disc':
                self.btn_disc_wid.background_color = [0.81, 0.27, 0.33, 1]
                self.btn_qty_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.btn_price_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.set_mode('Disc')
                try:
                    self.info = str(active_line.discount)
                except InvalidOperation:
                    print('decimal.InvalidOperation')
                print('Discount: ' + self.info)
            elif event == 'Price':
                self.btn_disc_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.btn_qty_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.btn_price_wid.background_color = [0.81, 0.27, 0.33, 1]
                self.set_mode('Price')
                try:
                    self.info = str(active_line.price)
                except InvalidOperation:
                    print('decimal.InvalidOperation')
                print('Price: ' + self.info)
            elif event == 'Qty':
                self.btn_disc_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.btn_price_wid.background_color = [0.2, 0.2, 0.2, 1.0]
                self.btn_qty_wid.background_color = [0.81, 0.27, 0.33, 1]
                self.set_mode('Qty')
                try:
                    self.info = str(active_line.qty)
                except InvalidOperation:
                    print('decimal.InvalidOperation')
                print('Qty: ' + str(self.info))
            elif event == 'Del':
                do_update_line = True
                if len(self.info) > 0:
                    self.info = self.info[:-1]
                else:
                    if len(self.my_data_view) > 0:
                        n = self.my_data_view[-1]
                        self.my_data_view.remove(n)
                        self._selected_line_index -= 1
                    else:
                        print('List is empty')
        if do_update_line:
            if self._mode == 'Qty':
                if len(self.info) > 0:
                    active_line.qty = Decimal(self.info)
                if len(self.info) == 0:
                    self.update_qty_disc_price(product_id, Decimal(1.0), active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_id, Decimal(self.info), active_line.discount, active_line.price)
            elif self._mode == 'Disc':
                if len(self.info) > 0:
                    active_line.discount = Decimal(self.info)
                if len(self.info) == 0:
                    self.update_qty_disc_price(product_id, active_line.qty, active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_id, active_line.qty, Decimal(self.info), active_line.price)
            elif self._mode == 'Price':
                if len(self.info) > 0:
                    active_line.price = Decimal(self.info)
                if len(self.info) == 0:
                    self.update_qty_disc_price(product_id, active_line.qty, active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_id, active_line.qty, active_line.discount, Decimal(self.info))
        print('mode: ' + self._mode +
              ' info: ' + self.info +
              ' product_id:' + product_id +
              ' qty:' + str(active_line.qty) +
              ' price:' + str(active_line.price) +
              ' discount:' + str(active_line.discount))
        self.label_wid.text = self.info
        print(str(self.get_total()))
        self.label_total_wid.text = 'Total: ' + self.format_currency_amount(self.get_total())


class MyTabbedPanel(TabbedPanel):
    def __init__(self, **kwargs):
        super(MyTabbedPanel, self).__init__(**kwargs)
        self.bind(current_tab=self.content_changed_cb)

    def switch_to(self, header):
        super(MyTabbedPanel, self).switch_to(header)
        print 'switch_to, content is ', header.text
        if self.parent is not None:
            posscreen = self.parent.parent.parent.parent
            for tab in self.tab_list:
                if not tab.text == '' and not tab.text == 'Home' and not tab.text == 'Search' and tab.text == header.text:
                    if len(self.content.children[0].children[0].children) > 0:
                        continue
                    self.content.children[0].children[0].clear_widgets()
                    with open('products.json') as data_file:
                        result = json.load(data_file)
                        products_json = result
                    for p in products_json['result']:
                        if header.text == p['category']:
                            p_id = str(p['id'])
                            if p['code'] is None or p['code'] == '':
                                subtext = p['name']
                            else:
                                subtext = p['code']
                            image_source = posscreen.get_local_image(p)
                            btn = Factory.CustomButton(image_source=image_source, id=p_id,
                                                       size_hint_y=None, width=300, height=100, subtext=subtext)
                            btn.bind(on_press=posscreen.do_add_item)
                            self.content.children[0].children[0].add_widget(btn)
                            print ('add local product ' + str(p['id']))

    def reset_tab_headers(self):
        for tab in self.tab_list:
            tab.background_color = [0.2, 0.2, 0.2, 1.0]

    def content_changed_cb(self, obj, value):
        self.reset_tab_headers()
        if value.text == 'Home':
            value.background_color = (0.81, 0.27, 0.33, 1)
            value.background_normal = ''
            value.background_down = ''
        elif value.text == 'Search':
            value.background_color = (0.81, 0.27, 0.33, 1)
            value.background_down = ''
            value.background_normal = ''
        else:
            print 'load category ' + value.text
            value.background_color = (0.81, 0.27, 0.33, 1)
            value.background_down = ''
            value.background_normal = ''

