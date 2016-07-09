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
