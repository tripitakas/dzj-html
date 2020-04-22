#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/add_pages.py --json_path=切分文件路径 [--img_path=页面图路径] [--txt_path=经文路径] [--kind=藏经类别码]
# python3 utils/update_db.py --uri=uri --func=init_variants


import re
import sys
import math
import pymongo
from os import path
from datetime import datetime

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.page.tool.variant import variants
from controller.page.base import PageHandler as Ph


def check_box_cover(db):
    """ 检查切分框的覆盖情况"""
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find({}, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), page['name']))
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
    for i in range(page_count):
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find({}, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), page['name']))
            old_chars_col = Ph.get_chars_col(page['chars'])
            blocks, columns, chars = Ph.reorder_boxes(page=page)
            new_chars_col = Ph.get_chars_col(chars)
            if not cmp_chars_col(old_chars_col, new_chars_col):
                print('invalid:', page['name'])


def init_variants(db):
    """ 初始化异体字表"""
    variants2insert = []
    for v_str in variants:
        for item in v_str:
            variants2insert.append(dict(txt=item, normal_txt=v_str[0]))
    db.variant.insert_many(variants2insert, ordered=False)
    print('add %s variants' % len(variants2insert))


def update_cid(db):
    """ 更新页面的cid"""
    size = 10
    page_count = math.ceil(db.page.count_documents({}) / size)
    for i in range(page_count):
        project = {'name': 1, 'chars': 1, 'blocks': 1, 'columns': 1}
        pages = list(db.page.find({}, project).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            update = dict()
            if Ph.update_box_cid(page['chars']):
                update['chars'] = page['chars']
            if Ph.update_box_cid(page['blocks']):
                update['blocks'] = page['blocks']
            if Ph.update_box_cid(page['columns']):
                update['columns'] = page['columns']
            if update:
                db.page.update_one({'_id': page['_id']}, {'$set': update})
            print('processing %s: %s' % (page['name'], 'updated' if update else 'keep'))


def main(db_name='tripitaka', uri='localhost', func='update_cid'):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
