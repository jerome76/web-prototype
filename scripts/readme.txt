cd /etc/init.d
sudo cp web-prototype.sh trytond.sh
sudo update-rc.d trytond.sh defaults
sudo service web-prototype restart
sudo update-rc.d erp-client.sh defaults
sudo update-rc.d web-prototype.sh defaults
sudo service erp-client restart



flask md: 5000
flask jc: 8080
tryton: 8000
erp-client: 8081

nohup gunicorn -b 0.0.0.0:5000 flask_shop:app &
nohup gunicorn -b 0.0.0.0:5001 flask_shop:app &



# install module company_logo
hg clone https://bitbucket.org/trytonspain/trytond-company_logo
rename to company_logo

source bin/activate
reload modules configuration:
./trytond-admin -c trytond.conf -d tryton_dev --all -v --dev
start server:
./trytond -c trytond.conf -v --dev -d tryton_dev

# insert frame in odt: image: (company.logo, 'image/png')
# logo 200x44 pixels png