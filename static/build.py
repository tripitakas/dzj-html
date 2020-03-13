#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 合并代码文件，压缩可用 http://tool.oschina.net/jscompress/
  运行本文件后将 static/built 下的 _*.html 移到发布版本的 views 下，其余的js和css可压缩后发布到built目录。
@time: 2019/7/12
"""
import re
import hashlib
from os import path, mkdir
from datetime import datetime

NEED_BUILD = ['base_css', 'base_js', 'base_cut']
PATH = path.dirname(path.dirname(__file__))
DST_PATH = path.join(PATH, 'static', 'built')


def merge_files(dst_name, files):
    ext = re.sub(r'^.+\.', '', files[0])
    content = '\n'.join(open(path.join(PATH, 'static', mf)).read() for mf in files)

    m = hashlib.md5()
    m.update(content.encode('utf-8'))
    ver = m.hexdigest()[:8]

    dst_name = '%s-%s.%s' % (dst_name, ver, ext)
    print(dst_name + ''.join('\n\t' + mf for mf in files))

    with open(path.join(DST_PATH, dst_name), 'w') as mf:
        mf.write(content)
        return dst_name


def merge_css_js(name, html_lines):
    css, js, lines, js_i = [], [], [], -1
    for text in html_lines:
        if re.match(r"<link .+static_url\('.+css'\)", text):
            fn = re.sub(r"^.+static_url\('|'\).+$", '', text)
            css.append(fn)
        elif re.match(r"<script .+static_url\('.+js'\)", text):
            fn = re.sub(r"^.+static_url\('|'\).+$", '', text)
            js.append(fn)
        elif text and not re.search(r'<!--\s*[^[]|^{%', text):
            if js_i < 0 and '<script>' in text:
                js_i = len(lines)
            if 'var resizefunc = [];' in text:
                js_i = -1
            if js_i < 0 and '</script>' in text:
                js_i = len(lines) + 1
            lines.append(text)

    filename = css and merge_files(name, css)
    if filename:
        css = '<link href="{{static_url(\'built/%s\')}}" rel="stylesheet" type="text/css" />' % filename
        if js_i >= 0:
            lines.insert(js_i, css)
        else:
            lines.append(css)

    filename = js and merge_files(name, js)
    if filename:
        js = '<script src="{{static_url(\'built/%s\')}}"></script>' % filename
        if js_i >= 0:
            lines.insert(js_i, js)
        else:
            lines.append(js)

    with open(path.join(PATH, 'views', '_%s_.html' % name), 'w') as f:
        f.write('\n'.join(lines))


def merge_from_html(names):
    for name in names:
        html_file = path.join(PATH, 'views', '_%s.html' % name)
        print(html_file)
        if path.exists(html_file):
            with open(html_file) as f:
                html_lines = f.read().split('\n')
            merge_css_js(name, html_lines)


def merge_assets(which=None):
    """ 合并第三方资源"""
    which = which or ['base_assets_css', 'base_assets_js', 'cut_assets_js',
                      'task_admin_assets_js', 'task_admin_assets_css']
    # 合并base css
    if 'base_assets_css' in which:
        files = [
            'assets/bootstrap/css/bootstrap.min.css',
            'assets/sweetalert2/sweetalert2.min.css',
            'assets/css/waves-effect.css',
            'assets/css/animate.css',
        ]
        dst_name = 'static/built/base_assets_%s.css' % datetime.now().strftime('%Y%m%d%H%M%S')
        content = '\n'.join(open(path.join(PATH, 'static', fn)).read() for fn in files)
        with open(path.join(PATH, dst_name), 'w') as fn:
            fn.write(content)

    # 合并base js
    if 'base_assets_js' in which:
        files = [
            'assets/jquery/jquery.slimscroll.min.js',
            'assets/bootstrap/js/bootstrap.min.js',
            'assets/sweetalert2/sweetalert2.min.js',
            'assets/sweetalert2/promise.min.js',
            'assets/modal-effect/js/classie.js',
            'assets/modal-effect/js/modalEffects.js',
        ]
        dst_name = 'static/built/base_assets_%s.js' % datetime.now().strftime('%Y%m%d%H%M%S')
        content = '\n'.join(open(path.join(PATH, 'static', fn)).read() for fn in files)
        with open(path.join(PATH, dst_name), 'w') as fn:
            fn.write(content)

    # 合并base_cut_js
    if 'cut_assets_js' in which:
        files = [
            'js/cut/raphael.js',
            'js/cut/raphael.zoom.js',
            'js/cut/jquery.mapkey.js',
        ]
        dst_name = 'static/built/cut_assets_%s.js' % datetime.now().strftime('%Y%m%d%H%M%S')
        content = '\n'.join(open(path.join(PATH, 'static', fn)).read() for fn in files)
        with open(path.join(PATH, dst_name), 'w') as fn:
            fn.write(content)

    # 合并task_admin_assets.js
    if 'task_admin_assets_js' in which:
        files = [
            'assets/select2/select2.min.js',
            'assets/select2/zh-CN.js',
            'assets/jquery-multi-select/jquery.multi-select.js',
            'assets/jquery-multi-select/jquery.quicksearch.js',
            'assets/flatpickr/flatpickr.js',
            'assets/flatpickr/zh.js',
        ]
        dst_name = 'static/built/task_admin_assets_%s.js' % datetime.now().strftime('%Y%m%d%H%M%S')
        content = '\n'.join(open(path.join(PATH, 'static', fn)).read() for fn in files)
        with open(path.join(PATH, dst_name), 'w') as fn:
            fn.write(content)

    # 合并task_admin_assets.css
    if 'task_admin_assets_css' in which:
        files = [
            'assets/jquery-multi-select/multi-select.css',
            'assets/flatpickr/flatpickr.min.css',
            'assets/select2/select2.css',
        ]
        dst_name = 'static/built/task_admin_assets_%s.css' % datetime.now().strftime('%Y%m%d%H%M%S')
        content = '\n'.join(open(path.join(PATH, 'static', fn)).read() for fn in files)
        with open(path.join(PATH, dst_name), 'w') as fn:
            fn.write(content)


if __name__ == '__main__':
    # if not path.exists(DST_PATH):
    #     mkdir(DST_PATH)
    # merge_from_html(NEED_BUILD)
    merge_assets(['task_admin_assets_css', 'task_admin_assets_js'])
