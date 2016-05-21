translate with:
pybabel extract -F babel.cfg -o messages.pot flask_shop
pybabel init -i messages.pot -d flask_shop/translations -l de
pybabel compile -d flask_shop/translations

update translation:
pybabel extract -F babel.cfg -o messages.pot flask_shop
pybabel update -i messages.pot -d flask_shop/translations
pybabel compile -d flask_shop/translations


