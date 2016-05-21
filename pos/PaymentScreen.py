import kivy
kivy.require('1.9.1')

from kivy.config import ConfigParser
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import Screen
import json
from decimal import Decimal
import uuid
import os
import traceback
#from escpos import *


class PaymentScreen(Screen):
    label_wid = ObjectProperty()
    text_input_wid = ObjectProperty()
    label_change_wid = ObjectProperty()
    icon_wid = ObjectProperty()

    def on_pre_enter(self, *args):
        print ('PaymentScreen on_pre_enter...')
        self.label_wid.text = str(self.manager.get_screen('posscreen').get_total())
        self.text_input_wid.text = ''
        self.label_change_wid.text = ''

    def getProduct(self, product_code):
        product_json = self.manager.get_screen('posscreen').products_json
        for i in product_json['result']:
            current_code = i['code']
            if current_code == product_code:
                return i
        return

    def do_action(self, event):
        print('Paymentscreen Button ' + str(event) + ' clicked.')
        if type(event) is int:
            amount_text = self.text_input_wid.text
            if len(amount_text) > 0:
                self.text_input_wid.text += str(event)
            else:
                self.text_input_wid.text = str(event)
        elif type(event) is str:
            if len(self.text_input_wid.text) > 0:
                if event == 'C':
                    self.text_input_wid.text = ''
                elif event == 'Del':
                    self.text_input_wid.text = self.text_input_wid.text[:-1]
                elif event == '.':
                    self.text_input_wid.text += str(event)

            if event == '+10':
                if len(self.text_input_wid.text) == 0:
                    self.text_input_wid.text = '0'
                amount = Decimal(self.text_input_wid.text) + Decimal(10.000)
                self.text_input_wid.text = str(amount)
            elif event == '+20':
                if len(self.text_input_wid.text) == 0:
                    self.text_input_wid.text = '0'
                amount = Decimal(self.text_input_wid.text) + Decimal(20.000)
                self.text_input_wid.text = str(amount)
            elif event == '+50':
                if len(self.text_input_wid.text) == 0:
                    self.text_input_wid.text = '0'
                amount = Decimal(self.text_input_wid.text) + Decimal(50.000)
                self.text_input_wid.text = str(amount)
        if len(self.text_input_wid.text) > 0:
            change = Decimal(self.text_input_wid.text) - self.manager.get_screen('posscreen').get_total()
            if change > Decimal(0.00):
                self.label_change_wid.text = str(change)
            else:
                self.label_change_wid.text = ''
        else:
            self.label_change_wid.text = ''

    def pay(self):
        unique_id = uuid.uuid4()

        def on_success(req, result):
            os.remove('offline/' + str(unique_id) + '.json')
            self.manager.get_screen('posscreen').icon_wid.source = 'icon.png'
            with open('sale.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            self.sale_json = result
            print ('on_success: sale returned.')
            self.manager.get_screen('posscreen').do_clear_item_list()
            self.parent.current = "posscreen"

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            print ('on_error: Could not send payment. Save to file instead.')
            self.manager.get_screen('posscreen').icon_wid.source = 'icon_offline.png'
            self.manager.get_screen('posscreen').do_clear_item_list()
            self.parent.current = "posscreen"

        try:
            print("Pay and clear list")
            payslip_json = dict([])
            payslip_positions = self.manager.get_screen('posscreen').my_data_view
            customer = dict([])
            customer['customerid'] = self.manager.get_screen('posscreen').customer_id
            payslip_json['customer'] = customer
            payslip_items = []
            for i in payslip_positions:
                print("selling: " + str(i))
                next_element = self.getProduct(i.product_code)
                if next_element is not None:
                    payslip_items.append(next_element)
            payslip_json['items'] = payslip_items
            with open('offline/' + str(unique_id) + '.json', 'w') as fp:
                json.dump(payslip_json, fp)
                fp.close()
            # clear list
            config = ConfigParser.get_configparser(name='app')
            print(config.get('serverconnection', 'server.url'))
            saleurl = config.get('serverconnection', 'server.url') + "pos/sale/"
            data_json = json.dumps(payslip_json)
            headers = {'Content-type': 'application/jsonrequest', 'Accept': 'application/jsonrequest'}
            if len(self.manager.get_screen('posscreen').my_data_view) > 0:
                UrlRequest(url=saleurl, on_success=on_success, on_failure=on_failure, on_error=on_error, req_headers=headers, req_body=data_json)
            else:
                self.manager.get_screen('posscreen').do_clear_item_list()
                self.parent.current = "posscreen"
        except Exception:
            print(traceback.format_exc())
            print "PaymentScreen.pay() Error: Could not send payslip"
