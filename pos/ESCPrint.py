import decimal
import time
from escpos import printer


class EscPrint:

    def __init__(self):
        pass

    @staticmethod
    def print_payslip(payslip, payslip_info):
        try:
            """ Seiko Epson Corp. Receipt Printer M129 Definitions (EPSON TM-T88IV) """
            # Epson = printer.Usb(0x04b8,0x0202)
            # Epson = printer.Usb(0x0416,0x5011,4,0x81,0x03)
            # Epson = printer.Serial(dev='/dev/rfcomm0', baudrate=9600, bytesize=8, timeout=1)
            # max line: Epson.text("012345678901234567890123456789012345678901\n")
            Epson = printer.Usb(0x04b8,0x0202)
            # Print image
            Epson.text("\n\n")
            Epson.image("logo.gif")
            # Print Header
            Epson.text("\n\n")
            Epson.set(align='center')
            Epson.text("Milliondog - the cosy company\n")
            Epson.text(time.strftime('%X %x %Z')+"\n")
            # Print text
            Epson.set(align='left')
            Epson.text("\n\n")
            Epson.text("Pos  Beschreibung                Betrag   \n")
            Epson.text("                                          \n")
            total = decimal.Decimal(0.00)
            for counter, payslip_line in enumerate(payslip):
                pos_left = str(counter) + "  " + payslip_line['code'] + " " + payslip_line['name']
                pos_right = payslip_line['price'] + " " + payslip_info['currency'] + "\n"
                Epson.text(pos_left + pos_right.rjust(42 - len(pos_left)))
                total = total + decimal.Decimal(payslip_line['price'])
            Epson.text("                                          \n")
            Epson.text("------------------------------------------\n")
            payslip_total = str(total) + " " + payslip_info['currency'] + "\n"
            Epson.text("Total :   " + payslip_total.rjust(42 - 10))
            # Print text
            Epson.text("\n\n")
            Epson.set(font='b', align='center')
            Epson.text("Powered by Semilimes\n")
            # Cut paper
            Epson.text("\n\n")
            Epson.cut()
        except AttributeError:
            print 'AttributeError: printer is probably not connected!'

