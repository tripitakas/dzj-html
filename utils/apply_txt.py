#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/apply_txt.py --uri=uri --func=find_cmp

import re
import sys
import math
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.tool.esearch import find_one
from controller.page.base import PageHandler as Ph


def find_cmp(db):
    """ 根据ocr文本，从cbeta库中寻找比对文本"""
    size = 10
    condition = {'cmp_txt': {'$in': [None, '']}}
    print('%s pages to process' % db.page.count_documents(condition))
    while db.page.count_documents(condition):
        pages = list(db.page.find(condition).sort('_id', 1).limit(size))
        for page in pages:
            print('[%s] processing %s' % (hp.get_date_time(), page['name']))
            ocr = Ph.get_txt(page, 'ocr')
            ocr = re.sub(r'■+', '', ocr)
            cmp_txt = find_one(ocr, only_match=True)[0]
            update = {'cmp_txt': cmp_txt} if cmp_txt else {'cmp_txt': cmp_txt, 'txt_match.cmp_txt': False}
            db.page.update_one({'_id': page['_id']}, {'$set': update})


def apply_txt(db, field):
    """ 适配文本至page['chars']，包括ocr_col, cmp_txt, txt等几种文本"""
    assert field in ['ocr_col', 'cmp_txt', 'txt']
    size = 10
    condition = {'txt_match.' + field: None}
    print('%s pages to process' % db.page.count_documents(condition))
    while db.page.count_documents(condition):
        pages = list(db.page.find(condition).sort('_id', 1).limit(size))
        for page in pages:
            if not Ph.get_txt(page, field):
                continue
            match, txt = Ph.apply_txt(page, field)
            update = {'chars': page['chars'], 'txt_match.' + field: {'status': match, 'value': txt}}
            db.page.update_one({'_id': page['_id']}, {'$set': update})
            print('[%s] processing %s: %s' % (hp.get_date_time(), page['name'], 'match' if match else 'not match'))


def migrate_txt_to_char(db, fields=None):
    """ 将page表的文本同步到char表"""
    fields = fields or ['ocr_col', 'cmp_txt', 'txt']
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    for i in range(page_count):
        project = {'name': 1, 'chars': 1, 'blocks': 1, 'columns': 1}
        pages = list(db.page.find({}, project).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s] processing %s' % (hp.get_date_time(), page['name']))
            for c in page['chars']:
                update = {f: c[f] for f in fields if c.get(f)}
                db.char.update_one({'name': '%s_%s' % (page['name'], c['cid'])}, {'$set': update})


def main(db_name='tripitaka', uri='localhost', func='find_cmp', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
