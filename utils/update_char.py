#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
# 更新数据库的char表

import re
import os
import sys
import math
import json
import pymongo
from os import path, walk
from collections import Counter
from operator import itemgetter
from functools import cmp_to_key

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph


def reset_img_need_updated(db):
    """ 根据字图，重置img_need_updated标记"""
    # 获取已有的字图名
    names = []
    src_dir = path.join(BASE_DIR, 'static', 'img', 'chars')
    for root, dirs, files in os.walk(src_dir):
        for fn in files:
            if not fn.startswith('.') and fn.endswith('.jpg'):
                name = fn.rsplit('_', 1)[0]
                names.append(name)
    print('%s char images found' % len(names))
    # 重置img_need_updated
    db.char.update_many({}, {'$set': {'img_need_updated': True}})
    size = 100000
    for i in range(math.ceil(len(names) / size)):
        print('processing page %s' % i)
        start = i * size
        db.char.update_many({'name': {'$in': names[start:start + size]}}, {'$set': {'img_need_updated': False}})


def update_un_required(db, source):
    """ 设置un_required标记"""
    size = 10000
    cond = {'source': source}
    item_count = db.char.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages to process' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['ocr_txt', 'alternatives', 'ocr_col', 'cmp_txt', 'name']
        chars = list(db.char.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        required, un_required = [], []
        for c in chars:
            if Ph.is_un_required(c):
                un_required.append(c['_id'])
            else:
                required.append(c['_id'])
        required and db.char.update_many({'_id': {'$in': required}}, {'$set': {'un_required': False}})
        un_required and db.char.update_many({'_id': {'$in': un_required}}, {'$set': {'un_required': True}})


def update_variant(db):
    counts = list(db.char.aggregate([
        {'$match': {'txt': {'$regex': r'Y\d+'}}},
        {'$group': {'_id': '$txt', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
    ]))
    vts = [c['_id'] for c in counts]
    for vt in vts:
        v_code = 'v' + hp.dec2code36(int(vt[1:]))
        print(vt, v_code)
        db.char.update_many({'txt': vt}, {'$set': {'txt': v_code}})


def update_txt_log(db):
    size, i = 20000, 0
    cond = {'need_updated': True}
    item_count = db.char.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    while db.char.find_one(cond):
        i += 1
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i, page_count))
        chars = list(db.char.find(cond, {'name': 1, 'txt_logs': 1, 'txt_type': 1}).limit(size))
        for c in chars:
            print(c.get('name'))
            update = {'need_updated': False}
            # reset char
            txt_type = c.pop('txt_type', 0)
            if txt_type == 'M':
                update['is_vague'] = True
            elif txt_type in ['N', '*']:
                update['uncertain'] = True
            # reset logs
            if c.get('txt_logs'):
                for log in c.get('txt_logs'):
                    txt_type = log.pop('txt_type', 0)
                    if txt_type == 'M':
                        log['is_vague'] = True
                    elif txt_type in ['N', '*']:
                        log['uncertain'] = True
                    if log.get('task_type') == 'rare_proof':
                        log['task_type'] = 'cluster_proof'
                update['txt_logs'] = c['txt_logs']
            db.char.update_one({'_id': c['_id']}, {'$set': update})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
