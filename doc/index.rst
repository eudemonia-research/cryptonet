.. Cryptonet documentation master file, created by
   sphinx-quickstart on Tue Jul  1 20:37:51 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Cryptonet
=========

Cryptonet is a blockchain library in python for Bitcoin-like protocols.

The project is quite young and the code will change a lot over the next
few months. You've been warned!

Getting started
---------------

Here's an example to get you started::

    from cryptonet import Cryptonet

    class Block(Cryptonet.Block):
        # Some block definition here.
        pass

    Block.GENESIS = Block(parameters)

    cryptonet = Cryptonet(seeds=[('cryptonet-example.eudemonia.io', 63656)],
                          address=('0.0.0.0', 63656),
                          block=Block,
                          rpc_address=('127.0.0.1', 17441))
    cryptonet.run()

This will connect to the network using the seeds provided, and will provide
the following RPC endpoints:

* **get_info** - returns general information about the cryptonet,
  such as block height.
* **push_tx** - broadcast a transaction to the network.
* **get_ledger** - this does something, but nobody really knows what.
* **get_balance** - returns the balance for a particular public key.

.. Welcome to Cryptonet's documentation!
   =====================================
   Contents:
   .. toctree::
   :maxdepth: 2
   Indices and tables
   ==================
   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`

