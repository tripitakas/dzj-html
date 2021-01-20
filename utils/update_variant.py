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
from controller.page.base import PageHandler as Ph


def init_variants(db):
    """ 初始化异体字表"""
    variants2insert = []
    for v_str in variants:
        for item in v_str:
            variants2insert.append(dict(txt=item, normal_txt=v_str[0]))
    db.variant.insert_many(variants2insert, ordered=False)
    print('add %s variants' % len(variants2insert))


def update_v_code(db, update_img=True):
    """ 重置v_code编码"""
    img_root = path.join(h.BASE_DIR, 'static/img')
    salt = h.prop(h.load_config(), 'web_img.salt')
    variant_list = list(db.variant.find({'uid': {'$ne': None}}, {'uid': 1, 'img_name': 1}))
    for v in variant_list:
        v_code = 'v' + h.dec2code36(v['uid'])
        db.variant.update_one({'_id': v['_id']}, {'$set': {'v_code': v_code}})
        if update_img and v.get('img_name'):
            inner_path = '/'.join(v['img_name'].split('_')[:-1])
            suffix = ('_' + h.md5_encode(v['img_name'], salt)) if salt else ''
            src_fn = 'chars/%s/%s%s.jpg' % (inner_path, v['img_name'], suffix)
            shutil.copy(path.join(img_root, src_fn), path.join(img_root, 'variants/%s.jpg' % v_code))


def update_user_txt(db):
    variant_list = list(db.variant.find({'img_name': {'$ne': None}}, {'img_name': 1, 'user_txt': 1, 'normal_txt': 1}))
    for v in variant_list:
        if v.get('img_name') and v.get('normal_txt'):
            db.variant.update_one({'_id': v['_id']}, {'$set': {'user_txt': v['normal_txt']}})


def main(db_name='tripitaka', uri='localhost', func='update_v_code', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished')
