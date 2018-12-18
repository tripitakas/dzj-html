#!/usr/bin/env python
# -*- coding: utf-8 -*-

from glob import glob
from os import path
import re


def sub_static_file(m):
    text = m.group()
    url = m.group(2)
    rel_name = re.sub(r'^[./]+', '', url)
    if path.exists(path.join(static_path, rel_name)):
        text = text.replace(url, "{{ static_url('%s') }}" % rel_name)
    return text


def scan_files(html_path):
    for fn in glob(path.join(html_path, '*.html')):
        with open(fn) as f:
            old = text = f.read()
        text = re.sub(r'(href|src)=[\'"]([A-Za-z0-9_./-]+)[\'"]', sub_static_file, text)
        if text != old:
            with open(fn, 'w') as f:
                print(fn)
                f.write(text)


static_path = path.join(path.dirname(__file__), '..', 'static')
scan_files(path.dirname(__file__))
