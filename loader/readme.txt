loader.py [type] [csv-file] [parameter]

# load customers by specifying 'customer' 'csv-file' 'country'
python loader.py customer us-500.csv 'US'
python loader.py customer swiss_customers.csv 'CH'


# load products by specifying 'product' 'csv-file' 'column-header-type'
python loader.py product test_products.csv A
python loader.py product articles.csv B


# pip install Pillow
# load images 'product' 'csv-file' 'column-header-type'
python loader.py image test_products.csv A
