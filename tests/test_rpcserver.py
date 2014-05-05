import unittest
import time
import sys

from cryptonet.rpcserver import RPCServer, RPCClient

class TestChain(unittest.TestCase):

    def setUp(self):
        self.test_server = RPCServer(port=32550)

        @self.test_server.add_method
        def echo(a_string):
            return a_string

        self.test_server.run()

        self.test_client = RPCClient(url="http://localhost:32550/jsonrpc")

        time.sleep(0.5)

    def test_methods(self):
        some_message = "Blah bloop foo bar"
        params = [some_message]
        echo_response = self.test_client.request("echo", params)
        assert echo_response["result"] == some_message

    def tearDown(self):
        print('Ctrl-C now')
        print('Ctrl-C now')
        pass

if __name__ == '__main__':
    unittest.main()