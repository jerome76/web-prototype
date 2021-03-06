import os
# THIS IS NEEDED FOR WINDOWS INSTALLER
# REMOVE THIS ON ANDROID: os.environ['KIVY_IMAGE'] = 'pil,sdl2'
os.environ['KIVY_IMAGE'] = 'pil,sdl2'
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.app import App
from POSScreen import *
from PaymentScreen import *


class MainScreen(Screen):
    textinput_user_wid = ObjectProperty()
    pass


class CustomerScreen(Screen):
    def on_pre_enter(self):
        def on_success(req, result):
            with open('customers.json', 'w') as fp:
                json.dump(result, fp)
                fp.close()
            self.products_json = result
            print ('customers loaded.')
            if len(result['result']) > 0:
                self.customer_list_wid.clear_widgets()
            for i in result['result']:
                cd_name = i['name']
                if i['name'] is None:
                    cd_name = str(i['id'])
                cd_address = i['street'], i['city'], i['zip'], str(i['country'])
                btn_text = cd_name.ljust(22) + ', '.join(item for item in cd_address if item)
                btn = Button(id=str(i['id']), text=btn_text, halign="left", valign="middle")
                btn.bind(on_press=self.do_action)
                btn.color = (0.1, 0.1, 0.1, 1)
                btn.font_size = '18sp'
                btn.background_color = (0.9, 0.9, 0.9, 1.0)
                btn.background_normal = ''
                btn.text_size[0] = self.size[0] * 0.9
                btn.size_hint_y = 0.05
                print ('add customer ' + str(i['id']))
                self.customer_list_wid.add_widget(btn)
            self.customer_list_wid.height = (len(result['result'])+4)*50

        def on_failure(req, result):
            on_error(req, result)

        def on_error(req, result):
            print 'could not load customers'
            try:
                with open('customers.json') as data_file:
                    result = json.load(data_file)
                    self.customer_list_wid.clear_widgets()
                for i in result['result']:
                    cd_name = i['name']
                    if i['name'] is None:
                        cd_name = str(i['id'])
                    cd_address = i['street'], i['city'], i['zip'], str(i['country'])
                    btn_text = cd_name.ljust(22) + ', '.join(item for item in cd_address if item)
                    btn = Button(id=str(i['id']), text=btn_text, halign="left", valign="middle")
                    btn.bind(on_press=self.do_action)
                    btn.color = (0.1, 0.1, 0.1, 1)
                    btn.font_size = '18sp'
                    btn.background_color = (0.9, 0.9, 0.9, 1.0)
                    btn.background_normal = ''
                    btn.text_size[0] = self.size[0] * 0.9
                    btn.size_hint_y = 0.05
                    print ('add customer ' + str(i['id']))
                    self.customer_list_wid.add_widget(btn)
                self.customer_list_wid.height = (len(result['result']) + 4) * 50
            except:
                traceback.print_exc(file=sys.stdout)

        try:
            print("Select Customer")
            self.label_wid.text = self.manager.get_screen('posscreen').customer_id
            # clear customer
            config = ConfigParser.get_configparser(name='app')
            print(config.get('serverconnection', 'server.url'))
            customerurl = config.get('serverconnection', 'server.url') + "pos/customers/"
            UrlRequest(customerurl, on_success=on_success, on_failure=on_failure, on_error=on_error)
        except:
            print "Error: Could not load products"

    def do_action(self, event):
        print('CustomerScreen Button was ' + str(event))
        self.label_wid.text = ('[' + event.id + '] ' + event.text)
        self.manager.get_screen('posscreen').customer_id = event.id
        self.manager.get_screen('posscreen').customer_name = self.manager.get_screen('posscreen').get_customer(event.id)["name"]
        self.manager.get_screen('posscreen').btn_customer_wid.text = self.manager.get_screen('posscreen').customer_name


class ScreenManagement(ScreenManager):
    pass

presentation = Builder.load_file("main.kv")

class MainApp(App):
    title = 'Semilimes Point-of-Sale'

    def build_config(self, config):
        config.setdefaults('section1', {
            'default_customer_id': 2,
            'default_payment_type': 'cash',
            'default_order_id': 1000,
            'hide_out_of_stock_items': True,
            'pos_printing_enabled': False,
            'bluetooth_printing_enabled': False,
            'download_images_after_sync': False
        })
        config.setdefaults('serverconnection', {
            'server.url': 'http://milliondog.ddns.net/'
        })

    def open_settings(self, *largs):
        self.config.set('section1', 'default_order_id', self.root.get_screen('posscreen').order_id)
        self.config.write()
        super(MainApp, self).open_settings()

    def close_settings(self, settings):
        super(MainApp, self).close_settings(settings)
        self.config.write()
        orderid = self.config.get('section1', 'default_order_id')
        self.root.get_screen('posscreen').order_id = int(orderid)
        self.root.get_screen('posscreen').btn_order_id_wid.text = str(orderid)

    def build_settings(self, settings):
        settings.add_json_panel('General settings',
            self.config, 'settings_custom.json')

    def on_pause(self):
        self.config.set('section1', 'default_order_id', self.root.get_screen('posscreen').order_id)
        self.config.write()
        return True

    def on_stop(self):
        self.config.set('section1', 'default_order_id', self.root.get_screen('posscreen').order_id)
        self.config.write()
        return True

    def on_start(self):
        self.root.get_screen('posscreen').order_id = self.config.get('section1', 'default_order_id')

    def on_resume(self):
        self.root.get_screen('posscreen').order_id = self.config.get('section1', 'default_order_id')

    def build(self):
        try:
            print (self.config.get('serverconnection', 'server.url'))
        except:
            print ('serverconnection is not set')

        return presentation

if __name__ == "__main__":
    Window.clearcolor = (0.6, 0.6, 0.6, 1)
    MainApp().run()