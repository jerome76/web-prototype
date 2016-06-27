installation

brew install postgresql

# bcrypt
sudo apt-get install libffi-dev
# Flask
sudo apt-get install libxml2-dev libxslt-dev
# pil
sudo apt-get install libjpeg-dev

pip install -r requirements.txt

install all tryton modules: (install_modules.sh)

install translations:
pybabel compile -d flask_shop/translations

