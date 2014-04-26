#!/usr/bin/env python

from distutils.core import setup

setup(name='Cryptonet',
      version='0.0.1',
      description='Blockchain and Cryptonet Framework',
      author='Max Kaye',
      author_email='max@eudemonia.io',
      packages=['cryptonet'],
      requires=['spore', 'encodium', 'pynacl', 'pysha3'],
     )

