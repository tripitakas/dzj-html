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


def reset_variant(db):
    counts = list(db.char.aggregate([
        {'$match': {'txt': {'$regex': r'Y\d+'}}},
        {'$group': {'_id': '$txt', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
    ]))
    vts = [c['txt'] for c in counts]
    for vt in vts:
        v_code = 'v' + hp.dec2code36(int(vt[1:]))
        print(vt, v_code)
        db.char.update_many({'txt': vt}, {'$set': {'txt': v_code}})


def update_txt_variant(ch):
    if len(ch.get('txt') or '') > 1 and ch['txt'][0] == 'Y':
        ch['txt'] = 'v' + hp.dec2code36(int(ch['txt'][1:]))
    if ch.get('txt_logs'):
        for log in ch.get('txt_logs'):
            if len(log.get('txt') or '') > 1 and log['txt'][0] == 'Y':
                log['txt'] = 'v' + hp.dec2code36(int(log['txt'][1:]))


def update_txt_type(ch):
    txt_type = ch.pop('txt_type', 0)
    if txt_type == 'M':
        ch['is_vague'] = True
    elif txt_type in ['N', '*']:
        ch['uncertain'] = True
    if ch.get('txt_logs'):
        for log in ch.get('txt_logs'):
            txt_type = log.pop('txt_type', 0)
            if txt_type == 'M':
                log['is_vague'] = True
            elif txt_type in ['N', '*']:
                log['uncertain'] = True
            if log.get('task_type') == 'rare_proof':
                log['task_type'] = 'cluster_proof'


def update_txt_logs(ch):
    logs = ch.get('txt_logs') or []
    for i, log in enumerate(logs):
        log.pop('nor_txt', 0)
        log.pop('txt_type', 0)
        for f in ['is_vague', 'is_deform', 'uncertain', 'remark']:
            if not log.get(f):
                log.pop(f, 0)
        valid = [f for f in ['is_vague', 'is_deform', 'uncertain', 'remark'] if log.get(f)]
        if not valid:
            if not log.get('txt') or log['txt'] == ch['ocr_txt']:
                log['invalid'] = True
    logs = [log for log in logs if not log.get('invalid')]
    if not logs:
        ch.pop('txt_logs', 0)
        ch.pop('txt_level', 0)
    else:
        ch['txt_logs'] = logs


def update_ocr_txt(ch):
    ch['ocr_txt'] = Ph.get_cmb_txt(ch)
    txts = [ch[k] for k in ['ocr_txt', 'ocr_col', 'cmp_txt'] if ch.get(k)]
    ch.get('alternatives') and txts.append(ch.get('alternatives')[:1])
    if not ch.get('txt_logs') and (not ch.get('txt') or ch['txt'] in txts):
        ch['txt'] = ch['ocr_txt']


def update_char_fields(db):
    fields = ['_id', 'name', 'page_name', 'char_id', 'uid', 'cid', 'source', 'has_img', 'img_need_updated',
              'lc', 'cc', 'pos', 'column', 'alternatives', 'ocr_col', 'cmp_txt', 'ocr_txt', 'is_diff',
              'un_required', 'txt', 'nor_txt', 'is_vague', 'is_deform', 'uncertain',
              'box_level', 'box_point', 'box_logs', 'txt_level', 'txt_point', 'txt_logs',
              'img_time', 'tasks', 'remark']

    cond = {}
    size = 20000
    item_count = db.char.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        chars = list(db.char.find(cond).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing task %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for ch in chars:
            print(ch['name'])
            update_txt_variant(ch)
            update_txt_type(ch)
            update_txt_logs(ch)
            update_ocr_txt(ch)
            # diff
            diff = ch.pop('diff', 0)
            if diff:
                ch['is_diff'] = True
            # fields
            ch = {k: v for k, v in ch.items() if k in fields}
            # unset
            unset = ['diff', 'txt_type']
            if not ch.get('txt_logs'):
                unset.append('txt_logs')
            if not ch.get('txt_level'):
                unset.append('txt_level')
            db.char.update_one({'_id': ch.pop('_id')}, {'$set': ch, '$unset': {k: 0 for k in unset}})


def main(db_name='tripitaka', uri='localhost', func='update_char_fields', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
