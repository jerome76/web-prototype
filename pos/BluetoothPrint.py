'''
The app must have BLUETOOTH and BLUETOOTH_ADMIN permissions (well, i didn't
tested without BLUETOOTH_ADMIN, maybe it works.)
Connect your device to your phone, via the bluetooth menu. After the
pairing is done, you'll be able to use it in the app.
Printer 0F:03:E0:C2:2C:C9
'''

from jnius import autoclass
import decimal
import time
import traceback
import sys

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
UUID = autoclass('java.util.UUID')

class BluetoothPrint():

    recv_stream = None
    send_stream = None
    device_name = 'BlueTooth Printer'

    def __init__(self):
        pass

    def get_socket_stream(name):
        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        socket = None
        for device in paired_devices:
            if device.getName() == name:
                socket = device.createRfcommSocketToServiceRecord(
                    UUID.fromString("00001101-0000-1000-8000-00805F9B34FB"))
                recv_stream = socket.getInputStream()
                send_stream = socket.getOutputStream()
                break
        socket.connect()
        return recv_stream, send_stream


    def reset(self):
        try:
            self.init(self.device_name)
            self.send('0\n')
        except:
            traceback.print_exc(file=sys.stdout)
            print("reset(): Printing failed.")

    def init(self, device_name):
        if self.send_stream is None:
            self.recv_stream, self.send_stream = self.get_socket_stream(device_name)

    def print_payslip(self, payslip, payslip_info):
        try:
            self.init(self.device_name)
            self.text(" Milliondog - the cosy company  ")
            self.text(time.strftime('%X %x %Z'))
            self.text("                                ")
            self.text("                                ")
            self.text("Anz  Beschreibung      Betrag   ")
            self.text("                                ")
            total = decimal.Decimal(0.00)
            for counter, payslip_line in enumerate(payslip):
                pos_left = payslip_line['item_qty'] + "  " + payslip_line['name']
                pos_right = payslip_line['price']
                self.text(pos_left + pos_right.rjust(32 - len(pos_left)))
                total = total + decimal.Decimal(payslip_line['price'])
                self.text("                                ")
            self.text("--------------------------------")
            payslip_total = payslip_info['currency'] + " " + str(total)
            self.text("Total :   " + payslip_total.rjust(32 - 10))
            self.text("                                ")
            self.text("                                ")
            self.text("     Powered by Semilimes       ")
            self.text("\n\n")
            self.flush()
        except:
            traceback.print_exc(file=sys.stdout)
            print("print_payslip(): Printing failed.")

    def text(self, text):
        self.send_stream.write('{}\n'.format(text))

    def flush(self):
        self.send_stream.flush()
