import kivy
kivy.require('1.9.1')

from kivy.config import ConfigParser
from kivy.properties import ObjectProperty
from kivy.network.urlrequest import UrlRequest
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
import json
from decimal import Decimal
import uuid
import re
import os
import traceback
from ESCPrint import EscPrint
from datetime import datetime


class FloatInput(TextInput):
    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class PaymentScreen(Screen):
    label_wid = ObjectProperty()
    text_input_wid = ObjectProperty()
    label_change_wid = ObjectProperty()
    icon_wid = ObjectProperty()

    def on_pre_enter(self, *args):
        print ('PaymentScreen on_pre_enter...')
        self.label_wid.text = self.format_currency_amount(self.manager.get_screen('posscreen').get_total())
        self.text_input_wid.text = ''
        self.label_change_wid.text = ''
        self.text_input_wid.focus = True

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
            if change >= Decimal(0.00):
                self.label_change_wid.color = (0, 0, 0, 1)
                self.label_change_wid.text = self.format_currency_amount(change)
            else:
                self.label_change_wid.color = (1, 0, 0, 1)
                self.label_change_wid.text = self.format_currency_amount(change)
        else:
            self.label_change_wid.text = ''

    def on_text(self, instance, value):
        print('PaymentScreen.on_text(FloatInput): ' + value.text)
        amount = Decimal(0.00)
        if value.text != '':
            amount = Decimal(value.text)
        change = amount - self.manager.get_screen('posscreen').get_total()
        if change >= Decimal(0.00):
            self.label_change_wid.color = (0, 0, 0, 1)
            self.label_change_wid.text = self.format_currency_amount(change)
        else:
            self.label_change_wid.color = (1, 0, 0, 1)
            self.label_change_wid.text = self.format_currency_amount(change)

    def format_currency_amount(self, amount):
        return '{:20,.2f}'.format(amount)

    def pay(self):
        unique_id = uuid.uuid4()
        order_id = self.manager.get_screen('posscreen').order_id

        def on_success(req, result):
            os.remove('offline/' + str(unique_id) + '.json')
            self.manager.get_screen('posscreen').update_icon(True)
            with open('sale.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            print ('on_success: sale returned.')
            if self.parent is not None:
                self.parent.current = "posscreen"

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            print ('on_error: Could not send payment. Saved to file instead.')
            self.manager.get_screen('posscreen').update_icon(False)
            if self.parent is not None:
                self.parent.current = "posscreen"

        try:
            print("Pay and clear list")
            payslip_json = dict([])
            payslip_positions = self.manager.get_screen('posscreen').my_data_view
            payslip_info = dict([])
            payslip_info['payslip_uuid'] = str(unique_id)
            payslip_info['order_id'] = str(order_id)
            payslip_info['order_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payslip_info['username'] = self.manager.get_screen('posscreen').username
            customer = dict([])
            customer['customerid'] = self.manager.get_screen('posscreen').customer_id
            payslip_json['customer'] = customer
            payslip_json['payslip_info'] = payslip_info
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
            # print payslip
            config = ConfigParser.get_configparser(name='app')
            print_enabled = config.get('section1', 'pos_printing_enabled')
            if print_enabled == 'True':
                EscPrint.print_payslip(payslip_items)
            saleurl = config.get('serverconnection', 'server.url') + "pos/sale/"
            print(config.get('serverconnection', 'server.url'))
            data_json = json.dumps(payslip_json)
            headers = {'Content-type': 'application/jsonrequest', 'Accept': 'application/jsonrequest'}
            if len(self.manager.get_screen('posscreen').my_data_view) > 0:
                UrlRequest(url=saleurl, on_success=on_success, on_failure=on_failure, on_error=on_error, req_headers=headers, req_body=data_json)
            else:
                self.parent.current = "posscreen"
            self.manager.get_screen('posscreen').do_clear_item_list()
            self.manager.get_screen('posscreen').order_id = order_id + 1
            self.parent.current = "posscreen"
        except Exception:
            print(traceback.format_exc())
            print "PaymentScreen.pay() Error: Could not send payslip"


