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
    def sub_ref(line):
        return re.sub(r'^.{{"|}}.+$|\s', '', line)

    with open(path.join(html_path, base_file)) as f:
        template = [sub_ref(t) for t in f.readlines() if 'static_url' in t]

    last_replaced = False
    ref = '{% include ' + base_file + ' %}'

    for fn in glob(path.join(html_path, '*.html')):
        if '_base_' in fn:
            continue
        with open(fn) as f:
            old = text = f.read()
            lines = text.split('\n')
        found = ref in text
        n = len(lines) - 1
        for i, t in enumerate(lines[::-1]):
            s = sub_ref(t)
            if s in template:
                last_replaced = True
                if not found:
                    found = True
                    lines[n - i] = re.sub(r'<.+$', ref, t)
                else:
                    lines.remove(t)
            elif last_replaced:
                if '<!--' in t or len(t) < 2:
                    lines.remove(t)
                else:
                    last_replaced = False
        lines = '\n'.join(lines)
        if lines != old:
            with open(fn, 'w') as f:
                print(fn)
                f.write(lines)


static_path = path.join(path.dirname(__file__), '..', 'static')
scan_dup_html(path.dirname(__file__), '_base_css.html')
