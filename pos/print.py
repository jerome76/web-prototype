from escpos import *
import time

""" Seiko Epson Corp. Receipt Printer M129 Definitions (EPSON TM-T88IV) """
# max line: Epson.text("012345678901234567890123456789012345678901\n")
#Epson = printer.Usb(0x04b8,0x0202)
#Epson = printer.Serial("COM1")
Epson = printer.Usb(0x0416,0x5011,4,0x81,0x03)
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
Epson.text("Anz  Beschreibung                Betrag   \n")
Epson.text("                                          \n")
Epson.text("1    200018 Cosy-Loop M-L        55.00 CHF\n")
Epson.text("1    200019 Cosy-Loop M-L        55.00 CHF\n")
Epson.text("                                          \n")
Epson.text("------------------------------------------\n")
Epson.text("Total :                         110.00 CHF\n")
# Print QR Code
Epson.text("\n\n")
Epson.set(align='center')
Epson.qr("http://milliondog.semilimes.com/")
Epson.text("http://milliondog.semilimes.com/\n")
# Print barcode
Epson.text("\n\n")
Epson.set(align='center')
#Epson.barcode('1000002000014','EAN13',64,2,'','')
# Print text
Epson.text("\n\n")
Epson.set(font='b', align='center')
Epson.text("Powered by Semilimes\n")
# Cut paper
Epson.text("\n\n")
Epson.cut()
