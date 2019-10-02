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
    db.page.create_index('name')
    task_types = ['cut_proof', 'cut_review', 'ocr_proof', 'ocr_review', 'text_proof_1', 'text_proof_2', 'text_proof_3',
                  'text_review']
    for task_type in task_types:
        db.page.create_index('tasks.%s.status' % task_type)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
