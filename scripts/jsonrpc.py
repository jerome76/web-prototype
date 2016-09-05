import requests
import json

class HttpClient:
    """HTTP Client to make JSON RPC requests to Tryton server.
    User is logged in when an object is created.
    """
    def __init__(self, url, database_name, user, passwd):
        self._url = '{}/{}/'.format(url, database_name)
        self._user = user
        self._passwd = passwd
        self._login()

    def _login(self):
        payload = json.dumps({
            'params': [self._user, self._passwd],
            'jsonrpc': "2.0",
            'method': 'common.db.login',
            'id': 1,
        })
        headers = {'content-type': 'application/json'}
        result = requests.post(self._url, data=payload, headers=headers)
        if 'json' in result:
            self._session = result.json()['result']
        else:
            self._session = json.loads(result.text)['result']
        return self._session

    def call(self, model, method):
        """RPC Call
        """
        method = '{}.{}.{}'.format('model', model, method)
        payload = json.dumps({
            'params': [
                self._session[0],
                self._session[1],
                [1, 2],
            ],
            'method': method,
            'id': 1
        })
        headers = {'content-type': 'application/json'}
        response = requests.post(self._url, data=payload, headers=headers)
        print response.json()
        return response.status_code


def main():
    url = "http://127.0.0.1:8000"
    headers = {'content-type': 'application/json'}
    client = HttpClient(url, "tryton_dev", "admin", "admin")
    status_code = client.call('ir.model', 'read')
    print status_code



def obsolete():
    url = "http://127.0.0.1:8000/tryton_dev/"
    headers = {'content-type': 'application/json'}

    # Example echo method
    payload = {
        "method": "common.db.login",
        "params": ["admin", "admin"],
        "jsonrpc": "2.0",
        "id": 1,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()

    print response
    assert response["id"] == 1
    cookie = '"' + response["result"][1] + '"'

    # Example echo method
    payload = {
        "method": "system.listMethods",
        "cookie": cookie,
        "params": [],
        "jsonrpc": "2.0",
        "id": 1,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()
    print response


if __name__ == "__main__":
    main()