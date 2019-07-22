#! /usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import controller.app as meta

site = meta.Application([]).config['site']
setup(
    name='tripitaka',
    version=meta.__version__,
    description=site['name'],
    keywords=site['keywords'],
    platforms='any',
    packages=find_packages() + ['controller'],
    package_data={
        'controller': [
            '../main.py',
            '../*.yml', '../requirements.txt', '../run_tests.py', '../tox.ini'
        ]
    },
    classifiers=[
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Natural Language :: Chinese (Simplified)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic'
    ],
    zip_safe=False
)
