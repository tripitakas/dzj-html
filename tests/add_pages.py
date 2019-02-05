#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 导入页面文件到文档库，可导入页面图到 static/img 供本地调试用
# python tests/add_pages.py --json_path=切分文件路径 [--img_path=页面图路径] [--txt_path=经文路径] [--kind=藏经类别码]

from tornado.util import PY3
from os import path, listdir, mkdir
import sys
import json
import re
import shutil
import pymongo
from datetime import datetime

IMG_PATH = path.join(path.dirname(__file__), '..', 'static', 'img')
data = dict(count=0)


def create_folder(filename):
    if not path.exists(filename):
        mkdir(filename)


def open_file(filename):
    return open(filename, encoding='UTF-8') if PY3 else open(filename)


def load_json(filename):
    if path.exists(filename):
        try:
            with open_file(filename) as f:
                return json.load(f)
        except Exception as e:
            sys.stderr.write('invalid file %s: %s\n' % (filename, str(e)))


def scan_dir(src_path, kind, db, ret):
    if not path.exists(src_path):
        sys.stderr.write('%s not exist\n' % (src_path,))
        return []
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            scan_dir(filename, fn if re.match(r'^[A-Z]{2}$', fn) else kind, db, ret)
        elif kind and fn[:2] == kind:
            if fn.endswith('.json') and fn[:-5] not in ret:
                info = load_json(filename)
                if info:
                    name = info.get('imgname')
                    if name != fn[:-5]:
                        sys.stderr.write('invalid imgname %s, %s\n' % (filename, kind))
                        continue
                    add_page(name, info, db)
                    ret.add(name)
            elif fn.endswith('.txt'):
                pass


def add_page(name, info, db):
    if not db.cutpage.find_one(dict(name=name)):
        meta = dict(name=name,
                    kind=name[:2],
                    width=int(info['imgsize']['width']),
                    height=int(info['imgsize']['height']),
                    blocks=info.get('blocks', []),
                    columns=info.get('columns', []),
                    chars=info.get('chars', []),
                    txt='',
                    create_time=datetime.now())
        data['count'] += 1
        print('%s:\t%d x %d blocks=%d columns=%d chars=%d' % (
            name, meta['width'], meta['height'], len(meta['blocks']), len(meta['columns']), len(meta['chars'])))
        db.cutpage.insert_one(meta)


def add_texts(src_path, pages, db):
    if not path.exists(src_path):
        return
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            add_texts(filename, pages, db)
        elif fn.endswith('.txt') and fn[:-4] in pages:
            with open_file(filename) as f:
                txt = f.read().strip().replace('\n', '|')
            r = db.cutpage.find_one(dict(name=fn[:-4]))
            if r and not r.get('txt'):
                db.cutpage.update_one(dict(name=fn[:-4]), {'$set': {'txt': txt}})


def copy_img_files(src_path, pages):
    if not path.exists(src_path):
        return
    create_folder(IMG_PATH)
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            copy_img_files(filename, pages)
        elif fn.endswith('.jpg') and fn[:-4] in pages:
            dst_file = path.join(IMG_PATH, fn[:2])
            create_folder(dst_file)
            dst_file = path.join(dst_file, fn)
            if not path.exists(dst_file):
                shutil.copy(filename, dst_file)


def main(json_path='', img_path='img', txt_path='txt', kind='', db_name='tripitaka', uri='localhost'):
    if not json_path:
        txt_path = json_path = path.join(path.dirname(__file__), 'data')
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    pages = set()
    scan_dir(json_path, kind, db, pages)
    copy_img_files(img_path, pages)
    add_texts(txt_path, pages, db)
    return data['count']


if __name__ == '__main__':
    import fire

    fire.Fire(main)
