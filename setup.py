#!/usr/bin/env python

from setuptools import setup

setup(name='Cryptonet',
      version='0.0.5',
      description='Blockchain and Cryptonet Framework',
      author='Max Kaye',
      author_email='max@eudemonia.io',
      packages=['cryptonet'],
      install_requires=['spore', 'encodium', 'pynacl', 'pysha3', 'pycoin', 'requests', 'werkzeug', 'json-rpc'],
     )

