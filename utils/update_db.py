#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_db.py --uri=uri --func=init_variants

import sys
import pymongo
from os import path
from pymongo.errors import PyMongoError

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.page.tool.variant import variants


def index_db(db):
    """ 给数据库增加索引"""
    fields2index = {
        'user': ['name', 'email', 'phone'],
        'page': ['name', 'page_code', 'source', 'tasks'],
        'char': ['name', 'source', 'uid', 'ocr_txt', 'txt', 'diff', 'un_required', 'cc', 'sc', 'txt_level', 'has_img'],
        'task': ['task_type', 'collection', 'id_name', 'doc_id', 'status'],
        'variant': ['txt', 'normal_txt'],
    }
    for collection, fields in fields2index.items():
        for field in fields:
            try:
                db[collection].create_index(field)
            except PyMongoError as e:
                print(e)


def init_variants(db):
    """ 初始化异体字表"""
    variants2insert = []
    for v_str in variants:
        for item in v_str:
            variants2insert.append(dict(txt=item, normal_txt=v_str[0]))
    db.variant.insert_many(variants2insert, ordered=False)
    print('add %s variants' % len(variants2insert))


def main(db_name='tripitaka', uri='localhost', func='index_db', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
