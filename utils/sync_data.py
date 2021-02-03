#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 数据同步
# python3 utils/sync_data.py --uri=xxx --func=xxx

import re
import sys
import math
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.char.char import Char
from controller.tool.esearch import find_match
from controller.page.base import PageHandler as Ph


def apply_cmp_txt(db, source, reset=None):
    """ 根据ocr文本，从cbeta库中寻找比对文本并适配至字框"""
    size = 1000
    cond = {'source': source}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['name', 'chars', 'cmp_txt']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]%s' % (hp.get_date_time(), page['name']))
            if not reset and 'cmp_txt' in page:
                continue
            txt = Ph.get_txt(page, 'txt')
            if not txt:
                continue
            cmp_txt = find_match(re.sub(r'■+', '', txt))
            mis_len = Ph.apply_raw_txt(page, cmp_txt, 'cmp_txt')
            update = {'chars': page['chars'], 'cmp_txt': cmp_txt, 'txt_match.cmp_txt.mis_len': mis_len}
            db.page.update_one({'_id': page['_id']}, {'$set': update})


def sync_page_to_char(db, source):
    """ 将page表的文本同步到char表"""
    size = 100
    cond = {'source': source}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages to process' % (hp.get_date_time(), item_count, page_count))
    added, deleted, updated, invalid = [], [], [], []
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['name', 'source', 'columns', 'chars']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for p in pages:
            print('[%s]processing %s' % (hp.get_date_time(), p['name']))
            if not p.get('chars') or not p.get('columns'):
                continue
            id2col = {col['column_id']: {k: col[k] for k in ['cid', 'x', 'y', 'w', 'h']} for col in p['columns']}
            for c in p['chars']:
                name = '%s_%s' % (p['name'], c.get('cid'))
                try:
                    if c.get('deleted'):
                        r = db.char.delete_one({'name': name})
                        r.deleted_count and deleted.append(name)
                        continue
                    ch = db.find_one({'name': name}, {'name': 1})
                    column = id2col.get('b%sc%s' % (c['block_no'], c['column_no']))
                    meta = Char.get_char_meta(c, p['name'], p.get('source'), column, ch is not None)
                    if ch:
                        db.char.update_one({'name': name}, {'$set': meta})
                        updated.append(name)
                    else:
                        db.char.insert_one(meta)
                        added.append(name)
                except KeyError as e:
                    invalid.append(name)


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)
    print('finished.')


if __name__ == '__main__':
    import fire

    fire.Fire(main)
