#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 文本适配
# 1. 文本获取。根据page的ocr文本，从CBETA获取比对文本
# 2. 文本匹配。将page的OCR列框文本(ocr_col)、比对文本(cmp_txt)以及校对文本(txt)与page的字框(page['chars'])匹配。
#       不匹配时，将进行裁剪或者填充占位符■
# 3. 文本回写。匹配后，将文本回写到page['chars']中
# 4. 文本同步。将page['chars']中的文本同步到char表
# python3 utils/apply_txt.py --uri=uri --func=find_cmp

import re
import sys
import math
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.tool.esearch import find_match
from controller.page.base import PageHandler as Ph


def is_valid(txt):
    return txt not in [None, '', '■']


def find_cmp_txt(db, source, reset=None):
    """ 根据ocr文本，从cbeta库中寻找比对文本"""
    size = 100
    cond = {'source': source}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    updated, ignored = [], []
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars', 'ocr', 'cmp_txt']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]%s' % (hp.get_date_time(), page['name']))
            if not reset and 'cmp_txt' in page:
                ignored.append(page['name'])
                continue
            ocr = Ph.get_txt(page, 'ocr')
            if not ocr:
                ignored.append(page['name'])
                continue
            cmp_txt = find_match(re.sub(r'■+', '', ocr))
            db.page.update_one({'_id': page['_id']}, {'$set': {'cmp_txt': cmp_txt}})
            updated.append(page['name'])
    print('%s updated: %s' % (len(updated), updated))
    print('%s ignored: %s' % (len(ignored), ignored))


def apply_page_txt(db, source, field, reset=None):
    """ 适配文本至page['chars']，包括ocr_col, cmp_txt, txt等几种文本"""
    size = 100
    cond = {'source': source}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    # reset
    field1 = 'txt_match.' + field
    reset and db.page.update_many(cond, {'$unset': {field1: ''}})
    # process
    updated, ignored = [], []
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        pages = list(db.page.find(cond).sort('_id', 1).skip(i * size).limit(size))
        for p in pages:
            print('[%s]%s' % (hp.get_date_time(), p['name']))
            if not reset and field1 in p:
                ignored.append(p['name'])
                continue
            if not Ph.get_txt(p, field):
                ignored.append(p['name'])
                continue
            match, txt = Ph.apply_raw_txt(p, field)
            db.page.update_one({'_id': p['_id']}, {'$set': {
                'chars': p['chars'], field1: {'status': match, 'value': txt}}})
            updated.append(p['name'])
    print('%s updated: %s' % (len(updated), updated))
    print('%s ignored: %s' % (len(ignored), ignored))


def migrate_page_to_char(db, source, fields=None):
    """ 将page表的文本同步到char表"""
    fields = fields or ['ocr_col', 'cmp_txt', 'txt']
    fields = fields.split(',') if isinstance(fields, str) else fields

    size = 10
    cond = {'source': source}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages to process' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        pages = list(db.page.find(cond, {k: 1 for k in ['name', 'chars']}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            for c in page['chars']:
                update = {f: c[f] for f in fields if c.get(f)}
                update and db.char.update_one({'name': '%s_%s' % (page['name'], c['cid'])}, {'$set': update})


def migrate_char_to_page(db):
    """ 从char表中将文本回page表"""
    size, i = 100, 0
    cond = {'need_updated': True}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    while db.page.find_one(cond):
        i += 1
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i, page_count))
        page_dict = dict()
        pages = list(db.page.find(cond, {k: 1 for k in ['name', 'chars']}).limit(size))
        db.page.update_many({'_id': {'$in': [p['_id'] for p in pages]}}, {'$set': {'need_updated': None}})
        # 同步更新以下字段
        fields = ['name', 'txt', 'nor_txt', 'is_vague', 'uncertain', 'is_deform', 'txt_level', 'txt_logs']
        chars = list(db.char.find({'page_name': {'$in': [p['name'] for p in pages]}}, {k: 1 for k in fields}))
        if not chars:
            continue
        for c in chars:
            c.pop('_id', 0)
            page_name, cid = c.pop('name', '').rsplit('_', 1)
            page_dict[page_name] = page_dict.get(page_name) or dict()
            page_dict[page_name][cid] = c
        for p in pages:
            print(p['name'])
            if page_dict.get(p['name']):
                for c in p['chars']:
                    c.update(page_dict[p['name']].get(str(c['cid'])) or {})
                db.page.update_one({'_id': p['_id']}, {'$set': {'chars': p['chars']}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished.')
