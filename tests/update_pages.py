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
    update = {
        'tasks': {
            'cut_proof': {'status': 'ready'},
            'cut_review': {'status': 'ready'},
            'ocr_proof': {'status': 'ready'},
            'ocr_review': {'status': 'ready'},
            'text_proof_1': {'status': 'ready'},
            'text_proof_2': {'status': 'ready'},
            'text_proof_3': {'status': 'ready'},
            'text_review': {'status': 'ready'},
        },
        'lock': {}
    }
    fields = ['cmp1', 'txt1_html', 'cmp2', 'txt2_html', 'cmp3', 'txt3_html']
    r = db.page.update_many({}, {'$set': update, '$unset': {k: '' for k in fields}})
    print('%s records updated!' % r.modified_count)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
