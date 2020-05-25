#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/apply_txt.py --uri=uri --func=find_cmp

import re
import sys
import math
import pymongo
from os import path
from datetime import datetime
from pymongo.errors import PyMongoError

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.tool.esearch import find_one
from controller.page.base import PageHandler as Ph


def find_cmp(db):
    """ 寻找比对文本"""
    size = 10
    page_count = math.ceil(db.page.count_documents({'cmp_txt': {'$in': [None, '']}}) / size)
    for i in range(page_count):
        pages = list(db.page.find({'cmp_txt': {'$in': [None, '']}}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('processing %s: %s chars' % (page['name'], len(page['chars'])))
            ocr = Ph.get_txt(page, 'ocr')
            cmp_txt = find_one(ocr, only_match=True)[0]
            update = {'cmp_txt': cmp_txt} if cmp_txt else {'cmp_txt': cmp_txt, 'txt_match.cmp_txt': False}
            db.page.update_one({'_id': page['_id']}, {'$set': update})


def apply_txt(db, field):
    """ 适配文本至page['chars']，包括ocr_col, cmp_txt, txt等几种情况"""
    assert field in ['ocr_col', 'cmp_txt', 'txt']
    size = 10
    page_count = math.ceil(db.page.count_documents({'txt_match.' + field: None}) / size)
    for i in range(page_count):
        pages = list(db.page.find({'txt_match.' + field: None}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('processing %s: %s chars' % (page['name'], len(page['chars'])))
            match, txt = Ph.apply_txt(page, field)
            update = {'chars': page['chars'], 'txt_match.' + field: True} if match else {'txt_match.' + field: False}
            db.page.update_one({'_id': page['_id']}, {'$set': update})
            print('match' if match else 'not match')


def main(db_name='tripitaka', uri='localhost', func='find_cmp', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    # main(func='apply_txt', field='cmp_txt')
    import fire

    fire.Fire(main)
