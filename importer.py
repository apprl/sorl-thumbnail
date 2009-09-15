import django
from apparelrow.apps.apparel.models import *
import csv

class fashionisland_dialect(csv.Dialect):
    lineterminator = '\n'
    delimiter = '|'
    quoting = csv.QUOTE_NONE

csv.register_dialect('fashionisland', fashionisland_dialect)

file = open('data.csv')

reader = csv.DictReader(file, fieldnames=('category', 'manufacturer', 'product_name', 'size', 'product_id', 'price', 'delivery_price', 'delivery_time', 'available', 'product_url', 'product_image_url', 'description', 'gender'), dialect='fashionisland')

for row in reader:
    print row
