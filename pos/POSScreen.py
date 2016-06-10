import kivy
kivy.require('1.9.1') # replace with your current kivy version !

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.config import Config, ConfigParser
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.progressbar import ProgressBar
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.image import Image
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
import json
import urllib2
from kivy.clock import Clock
from decimal import Decimal, InvalidOperation
from kivy.factory import Factory
from kivy.uix.popup import Popup
import os, os.path
import glob
import traceback
from functools import partial
import time
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

    def upload_payslips(self, fn, pb_inc, *args):
        def on_success(req, result):
            self.pb.value += pb_inc
            print("Progressbar is on {0}%".format(self.pb.value))
            os.remove(fn)
            if self.pb.value >= 99.9:
                self.popup.dismiss()

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            self.pb.value += pb_inc
            print("Progressbar is on {0}%".format(self.pb.value))
            if self.pb.value >= 99.9:
                self.popup.dismiss()

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
    product_code = None

    def __init__(self, product_code, text='', is_selected=False, qty=Decimal(1.00), discount=Decimal(0.00), price=Decimal(0.00)):
        self.text = text
        self.is_selected = is_selected
        self.qty = qty
        self.discount = discount
        self.price = price
        self.product_code = product_code


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
    sale_json = []
    customer_id = 0
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
        self.btn_customer_wid.text = 'Client: ' + str(self.customer_id)
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
            for i in result['result']:
                code = i['code']
                if code == '':
                    code = '200001'
                btn = Factory.CustomButton(image_source='./products/'+code+'-small.png', id=code,
                                           size_hint_y=None, width=300, height=100, subtext=code)
                btn.bind(on_press=self.do_add_item)
                self.products_list.append(btn)
                print ('add online product ' + code)
                self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
            self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*110

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
                for i in result['result']:
                    code = i['code']
                    if code == '':
                        code = '200001'
                    btn = Factory.CustomButton(image_source='./products/'+code+'-small.png', id=code,
                                               size_hint_y=None, width=300, height=100, subtext=code)
                    btn.bind(on_press=self.do_add_item)
                    self.products_list.append(btn)
                    print ('add local product ' + code)
                    self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
                self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*110

        try:
            self.btn_order_id_wid.text = str(self.order_id)
            self.username = self.manager.get_screen('main').textinput_user_wid.text
            config = ConfigParser.get_configparser(name='app')
            print(config.get('serverconnection', 'server.url'))
            producturl = config.get('serverconnection', 'server.url') + "pos/products/"
            self.text_input_wid.focus = True
            if len(self.products_list) == 0:
                UrlRequest(url=producturl, on_success=on_success, on_failure=on_failure, on_error=on_error)
            else:
                return
        except:
            traceback.print_exc(file=sys.stdout)
        print "Initialize products selection"

    def update_icon(self, online=True):
        offline = '-offline'
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
        except:
            traceback.print_exc(file=sys.stdout)

    def do_search(self):
        def on_success(req, result):
            print ('search success.')
            for i in result['result']:
                code = str(i['code'])
                if code == '':
                    code = '200001'
                btn = Factory.CustomButton(image_source='./products/'+code+'-small.png', id=code,
                                           size_hint_y=None, width=300, height=100, subtext=code)
                btn.bind(on_press=self.do_add_item)
                self.products_search_list.append(btn)
                self.my_tabbed_panel_wid.grid_layout_search_wid.add_widget(btn)
                self.my_tabbed_panel_wid.switch_to(self.my_tabbed_panel_wid.tab_search_wid)
            self.my_tabbed_panel_wid.grid_layout_search_wid.height = (len(result['result'])/4+4)*110

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            print ('POSScrean.search().on_error() ' + result)

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
            for i in result['result']:
                code = i['code']
                if code == '':
                    code = '200001'
                btn = Factory.CustomButton(image_source='./products/'+code+'-small.png', id=code,
                                           size_hint_y=None, width=300, height=100, subtext=code)
                btn.bind(on_press=self.do_add_item)
                self.products_list.append(btn)
                print ('add local product ' + code)
                self.my_tabbed_panel_wid.grid_layout_home_wid.add_widget(btn)
            self.my_tabbed_panel_wid.grid_layout_home_wid.height = (len(result['result'])/4)*110


    def getProduct(self, code):
        for i in self.products_json['result']:
            current_code = i['code']
            if current_code == code:
                return i
        return

    def do_clear_item_list(self):
        print('do_clear_item_list')
        del self.my_data_view[:]
        self._selected_line_index = 0
        self.list_view_wid.height = self.height * 0.6
        self.btn_order_id_wid.text = str(self.order_id)

    def do_add_item(self, event):
        print('Add product button <%s> state is <%s>' % (self, event))
        product = self.getProduct(event.id)
        if product is not None:
            newitem = DataItem(event.id, text="[" + str(product['code']) + "] " + product['name']
                                    + '               ' + str(Decimal(product['price']) * Decimal(1.000))
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
        '''
        if len(self.payslip_items_list) > 10:
            self.list_view_wid.height = (len(self.payslip_items_list)+4) * 48
        else:
            self.list_view_wid.height = self.height * 0.6
        '''
        print('do_add_item finished.')

    def selection_change(self, change):
        print('_selected_line_index: ', self._selected_line_index)
        print("selection_change: " + change.text + " " + str(change.is_selected))
        change.background_color = [1, 1, 1, 1]
        self.selected_value = 'Selected: {}'.format(change.text)
        self.label_total_wid.text = 'Total: ' + str(self.get_total())


    def update_qty_disc_price(self, product_code, quantity, discount, price):
        if self.list_view_wid.adapter.get_count() > 0:
            self.my_data_view[self._selected_line_index-1].qty = quantity
            product = self.getProduct(product_code)
            text = self.get_line(product, quantity, discount, price)
            self.my_data_view[self._selected_line_index-1].text = text
            if hasattr(self.list_view_wid, '_reset_spopulate'):
                self.list_view_wid.adapter.data.prop.dispatch(self.list_view_wid.adapter.data.obj())
            view = self.list_view_wid.adapter.get_view(self._selected_line_index-1)
            view.trigger_action(duration=0)

    def set_mode(self, mode):
        self._mode = mode
        self.info = ''

    def get_line(self, product, quantity, discount, price):
        return "[" + str(product['code']) + "] " + product['name'] \
               + '               ' \
               + str(price * quantity) + ' ' + self.default_currency + "\n"  \
               + '  ' + str(quantity) + ' ' + product['uom_symbol'] + ' at ' + str(price) + ' ' \
               + self.default_currency + " / " + product['uom_symbol'] \
               + '               ' + str(discount)

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
        product_code = active_line.product_code
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
                    self.update_qty_disc_price(product_code, Decimal(1.0), active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_code, Decimal(self.info), active_line.discount, active_line.price)
            elif self._mode == 'Disc':
                if len(self.info) > 0:
                    active_line.discount = Decimal(self.info)
                if len(self.info) == 0:
                    self.update_qty_disc_price(product_code, active_line.qty, active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_code, active_line.qty, Decimal(self.info), active_line.price)
            elif self._mode == 'Price':
                if len(self.info) > 0:
                    active_line.price = Decimal(self.info)
                if len(self.info) == 0:
                    self.update_qty_disc_price(product_code, active_line.qty, active_line.discount, active_line.price)
                else:
                    self.update_qty_disc_price(product_code, active_line.qty, active_line.discount, Decimal(self.info))
        print('mode: ' + self._mode +
              ' info: ' + self.info +
              ' product_code:' + product_code +
              ' qty:' + str(active_line.qty) +
              ' price:' + str(active_line.price) +
              ' discount:' + str(active_line.discount))
        self.label_wid.text = self.info
        print(str(self.get_total()))
        self.label_total_wid.text = 'Total: ' + str(self.get_total())


class MyTabbedPanel(TabbedPanel):
    def __init__(self, **kwargs):
        super(MyTabbedPanel, self).__init__(**kwargs)
        self.bind(current_tab=self.content_changed_cb)

    def switch_to(self, header):
        super(MyTabbedPanel, self).switch_to(header)
        print 'switch_to, content is ', header.text

    def content_changed_cb(self, obj, value):
        if value.text == 'Home':
            value.background_color = (0.81, 0.27, 0.33, 1)
            value.background_normal = ''
            value.background_down = ''
            self.tab_search_wid.background_color = [0.2, 0.2, 0.2, 1.0]
            self.tab_search_wid.background_color = [0.2, 0.2, 0.2, 1.0]
        if value.text == 'Search':
            value.background_color = (0.81, 0.27, 0.33, 1)
            value.background_down = ''
            value.background_normal = ''
            self.tab_home_wid.background_color = [0.2, 0.2, 0.2, 1.0]
            self.tab_home_wid.background_color = [0.2, 0.2, 0.2, 1.0]
