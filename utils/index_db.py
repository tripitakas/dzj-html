#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo


def main(db_name='tripitaka', uri='localhost'):
    """
    数据库加索引
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    """
    db = pymongo.MongoClient(uri)[db_name]
    # 创建索引，加速检索
    fields2index1 = {
        'user': ['name', 'email', 'phone'],
        'char': ['name', 'uid', 'source', 'ocr_txt', 'txt', 'cc', 'sc'],
        'page': ['name', 'page_code', 'source', 'level.box', 'level.text'],
        'task': ['task_type', 'collection', 'id_name', 'doc_id', 'status'],
    }
    for collection, fields in fields2index1.items():
        for field in fields:
            db[collection].create_index(field)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished.')
