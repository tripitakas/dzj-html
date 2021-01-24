#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_db.py --uri=uri --func=init_variants

import sys
import pymongo
from os import path
from pymongo.errors import PyMongoError


def index_db(db):
    """ 给数据库增加索引"""
    fields2index = {
        'user': ['name', 'email', 'phone'],
        'page': ['name', 'source', 'page_code'],
        'log': ['create_time', 'user_id', 'op_type'],
        'variant': ['txt', 'v_code', 'nor_txt', 'user_txt'],
        'char': ['name', 'source', 'ocr_txt', 'rvw_txt', 'txt', 'cc', 'lc', 'txt_level',
                 'is_diff', 'un_required', 'is_vague', 'is_deform', 'uncertain'],
        'task': ['batch', 'task_type', 'num', 'collection', 'doc_id', 'txt_kind', 'status',
                 'is_oriented', 'picked_user_id'],
    }
    for collection, fields in fields2index.items():
        for field in fields:
            try:
                db[collection].create_index(field)
            except PyMongoError as e:
                print(e)


def main(db_name='tripitaka', uri='localhost', func='index_db', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    uri_prod = 'mongodb://tripitaka-product:sm2019321-321.product@111.198.8.162:29019'
    db = pymongo.MongoClient(uri_prod)['tripitaka-product']
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
