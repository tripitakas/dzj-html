#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo


def main(db_name='tripitaka', uri='localhost', reset=False):
    """
    重置page表
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param reset: 是重置全部状态还是将旧版本数据库里缺失的任务字段补上
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
    if reset:
        fields = ['cmp1', 'txt1_html', 'cmp2', 'txt2_html', 'cmp3', 'txt3_html']
        r = db.page.update_many({}, {'$set': update, '$unset': {k: '' for k in fields}})
        print('%s records updated!' % r.modified_count)
    else:
        for t in update['tasks'].keys():
            r = db.page.update_many({'tasks.%s.status' % t: None}, {'$set': {'tasks.%s.status' % t: 'ready'}})
            if r.modified_count:
                print('%s %s records updated!' % (r.modified_count, t))


if __name__ == '__main__':
    import fire

    fire.Fire(main)
