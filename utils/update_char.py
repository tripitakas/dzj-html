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


def update_column_cid(db, name=None):
    """ 更新char表的column字段"""
    cond = {'name': {'$regex': name}} if name else {}
    pages = list(db.page.find(cond, {'name': 1, 'chars': 1, 'columns': 1}))
    print('[%s]%s pages to process' % (hp.get_date_time(), len(pages)))
    for page in pages:
        print('[%s]processing %s' % (hp.get_date_time(), page['name']))
        for co in page['columns']:
            chars = [c for c in page['chars'] if c['block_no'] == co['block_no'] and c['column_no'] == co['column_no']]
            char_names = ['%s_%s' % (page['name'], c['cid']) for c in chars]
            db.char.update_many({'name': {'$in': char_names}}, {'$set': {
                'column': {k: co[k] for k in ['cid', 'x', 'y', 'w', 'h']}
            }})


def update_char_un_required(db, source):
    """ 设置char表的un_required标记"""
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
            if c.get('cc', 0) >= 990 and c.get('cmp_txt', 0) == c.get('alternatives', '')[:1]:
                un_required.append(c['_id'])
            else:
                required.append(c['_id'])
        required and db.char.update_many({'_id': {'$in': required}}, {'$set': {'un_required': False}})
        un_required and db.char.update_many({'_id': {'$in': un_required}}, {'$set': {'un_required': True}})


def update_img_need_updated(db):
    # 初始设置为True
    db.char.update_many({}, {'$set': {'img_need_updated': True}})
    # 获取已有的字图名
    names = []
    src_dir = path.join(BASE_DIR, 'static', 'img', 'chars')
    for root, dirs, files in os.walk(src_dir):
        for fn in files:
            if not fn.startswith('.') and fn.endswith('.jpg'):
                name = fn.rsplit('_', 1)[0]
                names.append(name)
    print('%s char images found' % len(names))
    size = 100000
    for i in range(math.ceil(len(names) / size)):
        print('processing page %s' % i)
        start = i * size
        db.char.update_many({'name': {'$in': names[start:start + size]}}, {'$set': {'img_need_updated': False}})


def update_task_required_count(db, batch='', renew=False):
    """ 更新聚类任务-需要校对字数"""
    size = 1000
    cond = {'task_type': {'$regex': 'cluster_'}}
    batch and cond.update({'batch': batch})
    not renew and cond.update({'required_count': None})
    cnt = db.task.count_documents(cond)
    page_count = math.ceil(cnt / size)
    print('[%s]%s tasks to process' % (hp.get_date_time(), cnt))
    for i in range(page_count):
        field = 'ocr_txt'
        tasks = list(db.task.find(cond, {'params': 1}).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing task %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for task in tasks:
            params = task['params']
            txt_kinds = [p[field] for p in params if p.get(field)]
            cond2 = {field: {'$in': txt_kinds}, 'source': params[0]['source'], 'un_required': {'$ne': True}}
            required_count = db.char.count_documents(cond2)
            db.task.update_one({'_id': task['_id']}, {'$set': {'required_count': required_count}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
