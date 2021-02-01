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
from controller.char.char import Char
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


def group_update_variant(db):
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
    changed = False
    if len(ch.get('txt') or '') > 1 and ch['txt'][0] == 'Y':
        ch['txt'] = 'v' + hp.dec2code36(int(ch['txt'][1:]))
        changed = True
    if ch.get('txt_logs'):
        for log in ch.get('txt_logs'):
            if len(log.get('txt') or '') > 1 and log['txt'][0] == 'Y':
                log['txt'] = 'v' + hp.dec2code36(int(log['txt'][1:]))
                changed = True
    return changed


def update_txt_type(ch):
    changed = False
    txt_type = ch.pop('txt_type', 0)
    if txt_type:
        changed = True
    if txt_type == 'M':
        ch['is_vague'] = True
    elif txt_type in ['N', '*']:
        ch['uncertain'] = True
    if ch.get('txt_logs'):
        for log in ch.get('txt_logs'):
            txt_type = log.pop('txt_type', 0)
            if txt_type:
                changed = True
            if txt_type == 'M':
                log['is_vague'] = True
            elif txt_type in ['N', '*']:
                log['uncertain'] = True
            if log.get('task_type') == 'rare_proof':
                log['task_type'] = 'cluster_proof'
                changed = True
    for f in ['is_vague', 'is_deform', 'uncertain', 'remark']:
        if f in ch and not ch.get(f):
            ch.pop(f, 0)
            changed = True
    return changed


def update_txt_logs(ch):
    changed = False
    logs = ch.get('txt_logs') or []
    for i, log in enumerate(logs):
        for f in ['nor_txt', 'txt_type']:
            if log.get(f):
                log.pop(f, 0)
                changed = True
        for f in ['is_vague', 'is_deform', 'uncertain', 'remark']:
            if not log.get(f):
                log.pop(f, 0)
                changed = True
        valid = [f for f in ['is_vague', 'is_deform', 'uncertain', 'remark'] if log.get(f)]
        if not valid:
            if not log.get('txt') or log['txt'] == ch['ocr_txt']:
                log['invalid'] = True
                changed = True
    logs = [log for log in logs if not log.get('invalid')]
    if not logs:
        for f in ['txt_logs', 'txt_level']:
            if f in ch:
                ch.pop(f, 0)
                changed = True
    else:
        ch['txt_logs'] = logs
    return changed


def update_ocr_txt(ch):
    changed = False
    cmb_txt = Char.get_cmb_txt(ch)
    if cmb_txt != ch['ocr_txt']:
        ch['ocr_txt'] = cmb_txt
        changed = True
    txts = [ch[k] for k in ['ocr_txt', 'ocr_col', 'cmp_txt'] if ch.get(k)]
    ch.get('alternatives') and txts.append(ch.get('alternatives')[:1])
    if not ch.get('txt_logs') and (not ch.get('txt') or ch['txt'] in txts):
        if ch['txt'] != cmb_txt:
            ch['txt'] = cmb_txt
            changed = True
    return changed


def update_char(db):
    size = 20000
    cond = {'source': '练习数据'}
    item_count = db.char.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        chars = list(db.char.find(cond).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing task %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for ch in chars:
            cmb_txt = Char.get_cmb_txt(ch)
            db.char.update_one({'_id': ch['_id']}, {'$set': {'cmb_txt': cmb_txt}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
