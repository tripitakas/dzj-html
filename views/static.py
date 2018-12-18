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


def scan_dup_html(html_path, base_file):
    with open(path.join(html_path, base_file)) as f:
        template = [re.sub(r'\s', '', t) for t in f.readlines() if 'static_url' in t]
    for fn in glob(path.join(html_path, '*.html')):
        if '_base_' in fn:
            continue
        with open(fn) as f:
            lines = f.readlines()
        found = False
        n = len(lines) - 1
        for i, t in enumerate(lines[::-1]):
            s = re.sub(r'\s', '', t)
            if s in template:
                if not found:
                    found = True
                    lines[n - i] = re.sub(r'<.+$', '{% include ' + base_file + ' %}', t)
                else:
                    lines.remove(t)
        if found:
            with open(fn, 'w') as f:
                print(fn)
                f.writelines(lines)


static_path = path.join(path.dirname(__file__), '..', 'static')
scan_dup_html(path.dirname(__file__), '_base_js.html')
