#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
# 更新数据库的char表

import re
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


def update_ocr_txt(db, include_txt=True):
    """ char表的ocr_txt"""

    def is_valid(_txt):
        return _txt not in [None, '', '■']

    size = 1000
    cond = {'source': '60华严'}
    page_count = math.ceil(db.char.count_documents(cond) / size)
    print('[%s]%s chars to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        fields = ['name', 'alternatives', 'ocr_txt', 'ocr_col', 'cmp_txt', 'txt', 'cc']
        chars = list(db.char.find(cond, {f: 1 for f in fields}).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing %s' % (hp.get_date_time(), [ch['name'] for ch in chars]))
        for ch in chars:
            txts = [ch.get('alternatives') and ch['alternatives'][0], ch.get('ocr_col'), ch.get('cmp_txt')]
            txts = [t for t in txts if is_valid(t)]
            c = Counter(txts).most_common(1)[0]
            ocr_txt = ch['alternatives'][0]
            if int(c[1]) > 1:
                ocr_txt = c[0]
            elif ch['cc'] > 960:
                ocr_txt = ch['alternatives'][0]
            elif is_valid(ch.get('cmp_txt')):
                ocr_txt = ch['cmp_txt']
            update = {'ocr_txt': ocr_txt, 'txt': ocr_txt} if include_txt else {'ocr_txt': ocr_txt}
            db.char.update_one({'_id': ch['_id']}, {'$set': update})


def update_txt(db):
    """ char表的txt"""
    size = 1000
    cond = {'source': '60华严'}
    page_count = math.ceil(db.char.count_documents(cond) / size)
    print('[%s]%s chars to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        project = {'name': 1, 'txt': 1, 'alternatives': 1, 'ocr_txt': 1, 'ocr_col': 1, 'cc': 1}
        chars = list(db.char.find(cond, project).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing page %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for ch in chars:
            if ch['txt'] != ch['ocr_txt'] and ch['ocr_txt'] not in ['', None, '■'] and (
                    ch['ocr_txt'] == ch['ocr_col'] or ch['cc'] > 900):
                db.char.update_one({'_id': ch['_id']}, {'$set': {'txt': ch['ocr_txt'], 'txt_bak': ch['txt']}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
