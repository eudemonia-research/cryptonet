'''Basically wrap https://github.com/pavlov99/json-rpc/blob/master/examples/server.py in an easy to use class'''

from threading import Thread
import requests
import json

from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple

from jsonrpc import JSONRPCResponseManager, dispatcher


class RPCServer(object):
    """ Example of json-rpc usage with Wergzeug and requests.

    NOTE: there are no Werkzeug and requests in dependencies of json-rpc.
    NOTE: server handles all url paths the same way (there are no different urls).

    """

    def __init__(self, port=32550, host='localhost'):
        self.port = port
        self.host = host

    @Request.application
    def application(self, request):
        # Dispatcher is dictionary {<method_name>: callable}
        response = JSONRPCResponseManager.handle(request.get_data(cache=False, as_text=True), dispatcher)
        return Response(response.json, mimetype='application/json')

    def run(self):
        self.my_thread = Thread(target=run_simple, args=(self.host, self.port, self.application))
        self.my_thread.start()

    def add_method(self, method):
        dispatcher.add_method(method)


class RPCClient(object):
    def __init__(self, url="http://localhost:4000/jsonrpc", username=b'', password=b''):
        self.url = url
        self.headers = {'content-type': 'application/json'}
        self.username = username
        self.password = password

    def request(self, method_name, params):
        payload = {
            "method": method_name,
            "params": params,
            "jsonrpc": "2.0",
            "id": 0,
        }
        return requests.post(self.url, data=json.dumps(payload), headers=self.headers, auth=(self.username, self.password)).json()