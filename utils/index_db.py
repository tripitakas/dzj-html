#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo


def main(db_name='tripitaka', uri='localhost'):
    """
    重置page表
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    """
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    fields2index = {
        'page': ['name'],
        'user': ['name', 'email', 'phone'],
        'task': ['task_type', 'collection', 'id_name', 'doc_id', 'status'],
    }
    for collection, fields in fields2index.items():
        for field in fields:
            db[collection].create_index(field)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
