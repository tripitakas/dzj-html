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
from controller.page.tool.esearch import find_match
from controller.page.base import PageHandler as Ph


def find_cmp(db, source):
    """ 根据ocr文本，从cbeta库中寻找比对文本"""
    size = 10
    cond = {'source': source}
    page_count = math.ceil(db.page.count_documents(cond) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            ocr = Ph.get_txt(page, 'ocr')
            ocr = re.sub(r'■+', '', ocr)
            cmp_txt = find_match(ocr)
            db.page.update_one({'_id': page['_id']}, {'$set': {'cmp_txt': cmp_txt}})


def apply_txt(db, source, field, reset=None):
    """ 适配文本至page['chars']，包括ocr_col, cmp_txt, txt等几种文本"""
    size = 10
    cond = {'source': source}
    page_count = math.ceil(db.page.count_documents(cond) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    reset and db.page.update_many(cond, {'$unset': {'txt_match.' + field: ''}})
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            if not Ph.get_txt(page, field):
                print('[%s]processing %s: %s not exist' % (hp.get_date_time(), page['name'], field))
                continue
            match, txt = Ph.apply_txt(page, field)
            update = {'chars': page['chars'], 'txt_match.' + field: {'status': match, 'value': txt}}
            db.page.update_one({'_id': page['_id']}, {'$set': update})
            print('[%s]processing %s: %s' % (hp.get_date_time(), page['name'], 'match' if match else 'not match'))


def migrate_page_txt_to_char(db, source, fields=None):
    """ 将page表的文本同步到char表"""
    fields = fields or ['ocr_col', 'cmp_txt', 'txt']
    if isinstance(fields, str):
        fields = fields.split(',')

    size = 10
    cond = {'source': source}
    page_count = math.ceil(db.page.count_documents(cond) / size)
    for i in range(page_count):
        project = {'name': 1, 'chars': 1, 'blocks': 1, 'columns': 1}
        pages = list(db.page.find(cond, project).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            for c in page['chars']:
                update = {f: c[f] for f in fields if c.get(f)}
                update and db.char.update_one({'name': '%s_%s' % (page['name'], c['cid'])}, {'$set': update})


def set_diff_symbol(db, source):
    """ 设置char表的diff标记"""

    def is_valid(_txt):
        return _txt not in [None, '', '■']

    size = 5000
    cond = {'source': source}
    page_count = math.ceil(db.char.count_documents(cond) / size)
    for i in range(page_count):
        print('[%s]processing page %s of each %s records.' % (hp.get_date_time(), i, size))
        projection = {k: 1 for k in ['ocr_txt', 'alternatives', 'ocr_col', 'cmp_txt', 'name']}
        chars = list(db.char.find(cond, projection).sort('_id', 1).skip(i * size).limit(size))
        diff, same = [], []
        for c in chars:
            txts = [c.get('alternatives') and c['alternatives'][0], c.get('ocr_col'), c.get('cmp_txt')]
            if len(set(t for t in txts if is_valid(t))) > 1:
                diff.append(c['_id'])
            else:
                same.append(c['_id'])
        db.char.update_many({'_id': {'$in': diff}}, {'$set': {'diff': True}})
        db.char.update_many({'_id': {'$in': same}}, {'$set': {'diff': False}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)
    print('finished.')


if __name__ == '__main__':
    import fire

    fire.Fire(main)
