#!/usr/bin/env python

from setuptools import setup

setup(name='Cryptonet',
      version='0.0.5',
      description='Blockchain and Cryptonet Framework',
      author='Max Kaye',
      author_email='max@eudemonia.io',
      packages=['cryptonet'],
      # NOTE(kitten): temporarily removing pysha3 because it is fucking with readthedocs (no compliation allowed on there).
      #install_requires=['spore', 'encodium', 'pynacl', 'pysha3', 'pycoin', 'requests', 'werkzeug', 'json-rpc'],
      install_requires=['spore', 'encodium', 'pynacl', 'pycoin', 'requests', 'werkzeug', 'json-rpc'],
     )

