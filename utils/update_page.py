#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
# 更新数据库的page表

import re
import sys
import math
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph


def reorder_boxes(db):
    """ 切分框(包括栏框、列框、字框)重新排序"""
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find({}, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            Ph.reorder_boxes(page=page)
            db.page.update_one({'_id': page['_id']}, {'$set': {
                'blocks': page['blocks'], 'columns': page['columns'], 'chars': page['chars']
            }})


def check_box_cover(db):
    """ 检查切分框(包括栏框、列框、字框)的覆盖情况"""
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find({}, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            valid, message, field, invalid_ids = Ph.check_box_cover(page)
            if not valid:
                print('%s: %s' % (message, invalid_ids))


def check_chars_col(db):
    """ 检查字序是否准确"""

    def cmp_chars_col(chars_cols1, chars_cols2):
        if len(chars_cols1) != len(chars_cols2):
            return False
        for n, chars_col1 in enumerate(chars_cols1):
            for m, cid1 in enumerate(chars_col1):
                cid2 = chars_cols2[n][m] if len(chars_cols2[n]) > m else 0
                if cid1 != cid2:
                    return False
        return True

    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find({}, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            old_chars_col = Ph.get_chars_col(page['chars'])
            blocks, columns, chars = Ph.reorder_boxes(page=page)
            new_chars_col = Ph.get_chars_col(chars)
            if not cmp_chars_col(old_chars_col, new_chars_col):
                print('invalid:', page['name'])


def update_cid(db):
    """ 更新切分框(包括栏框、列框、字框)的cid"""
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    print('[%s]%s pages to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        project = {'name': 1, 'chars': 1, 'blocks': 1, 'columns': 1}
        pages = list(db.page.find({}, project).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            updated = Ph.update_page_cid(page)
            if updated:
                update = {k: page.get(k) for k in ['chars', 'columns', 'blocks']}
                db.page.update_one({'_id': page['_id']}, {'$set': update})


def trim_txt_blank(db):
    """ 去除page['txt']字段中的空格"""
    pages = list(db.page.find({'txt': {'$nin': ['', None]}}, {'txt': 1, 'name': 1}))
    print('[%s]%s pages to process' % (hp.get_date_time(), len(pages)))
    for page in pages:
        print('[%s]processing %s' % (hp.get_date_time(), page['name']))
        db.page.update_one({'_id': page['_id']}, {'$set': {'txt': re.sub(r'\s', '', page['txt'])}})


def update_page_ocr(db):
    """ 根据page['chars']更新page['ocr']"""
    pages = list(db.page.find({}, {'name': 1, 'chars': 1}))
    for p in pages:
        print('processing page %s' % p['name'])
        ocr = Ph.get_box_ocr(p['chars'], 'char')
        db.page.update_one({'_id': p['_id']}, {'$set': {'ocr': ocr}})


def update_task_char_count(db):
    """ 更新页任务的char_count"""
    tasks = db.task.find({'char_count': None, 'collection': 'page'}, {'doc_id': 1})
    names = [p['doc_id'] for p in list(tasks)]
    pages = db.page.find({'name': {'$in': names}}, {'chars': 1, 'name': 1})
    print('[%s]%s pages to process' % (hp.get_date_time(), len(pages)))
    for page in pages:
        print('[%s]processing %s' % (hp.get_date_time(), page['name']))
        db.task.update_many({'char_count': None, 'collection': 'page', 'doc_id': page['name']},
                            {'$set': {'char_count': len(page['chars'])}})


def update_page_ocr_txt(db):
    """ page表的ocr_txt"""
    pages = list(db.page.find({}, {'chars': 1, 'name': 1}))
    print('[%s]%s pages to process' % (hp.get_date_time(), len(pages)))
    for page in pages:
        print('[%s]processing %s' % (hp.get_date_time(), page['name']))
        for ch in page.get('chars', []):
            if ch.get('alternatives'):
                ch['ocr_txt'] = ch['alternatives'][0]
        db.page.update_one({'_id': page['_id']}, {'$set': {'chars': page['chars']}})


def update_char_ocr_txt(db):
    """ char表的ocr_txt"""
    size = 1000
    page_count = math.ceil(db.char.count_documents({}) / size)
    print('[%s]%s chars to process' % (hp.get_date_time(), page_count))
    for i in range(page_count):
        project = {'alternatives': 1, 'name': 1}
        chars = list(db.char.find({}, project).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing %s' % (hp.get_date_time(), [ch['name'] for ch in chars]))
        for ch in chars:
            if ch.get('alternatives'):
                db.char.update_one({'_id': ch['_id']}, {'$set': {'ocr_txt': ch['alternatives'][0]}})


def main(db_name='tripitaka', uri='localhost', func='update_char_ocr_txt', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
