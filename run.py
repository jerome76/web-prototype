#!/media/ubuntu/dev/tryton/tryton3.8/bin/python
from flask_shop import app

app.run(host='0.0.0.0', port=5000, debug=True)
