#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
import re
import sys
import math
import json
import shutil
import pymongo
from os import path, walk
from datetime import datetime
from operator import itemgetter

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as h
from controller.page.tool.variant import variants


def init_variants(db):
    """ 初始化异体字表"""
    variants2insert = []
    for v_str in variants:
        for item in v_str:
            variants2insert.append(dict(txt=item, normal_txt=v_str[0]))
    db.variant.insert_many(variants2insert, ordered=False)
    print('add %s variants' % len(variants2insert))


def update_variant(db, fields='v_code,user_txt,img_name'):
    """ 重置v_code编码"""
    img_root = path.join(h.BASE_DIR, 'static/img')
    salt = h.prop(h.load_config(), 'web_img.salt')
    vts = list(db.variant.find({'uid': {'$ne': None}}, {'uid': 1, 'img_name': 1, 'user_txt': 1, 'normal_txt': 1}))
    for v in vts:
        update = {}
        v_code = 'v' + h.dec2code36(v['uid'])
        if 'v_code' in fields:
            update['v_code'] = v_code
        if 'user_txt' in fields and v.get('normal_txt'):
            update['user_txt'] = v.get('user_txt') or v['normal_txt']
        if 'img_name' in fields and v.get('img_name'):
            inner_path = '/'.join(v['img_name'].split('_')[:-1])
            suffix = ('_' + h.md5_encode(v['img_name'], salt)) if salt else ''
            src_fn = 'chars/%s/%s%s.jpg' % (inner_path, v['img_name'], suffix)
            shutil.copy(path.join(img_root, src_fn), path.join(img_root, 'variants/%s.jpg' % v_code))
        db.variant.update_one({'_id': v['_id']}, {'$set': update})


def main(db_name='tripitaka', uri='localhost', func='update_variant', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished')
