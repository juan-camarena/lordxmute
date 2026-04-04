import qrcode
import io

network_url = "http://192.168.1.5:6767"
qr = qrcode.QRCode(version=1, box_size=1, border=1)
qr.add_data(network_url)
qr.make(fit=True)

f = io.StringIO()
qr.print_ascii(out=f)
print("Option 2:")
print(f.getvalue())
