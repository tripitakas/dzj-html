#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo


def main(db_name='tripitaka', uri='localhost'):
    """
    重置page表字段
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    """
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    fields = ['tasks', 'cmp1', 'txt1_html', 'cmp2', 'txt2_html', 'cmp3', 'txt3_html']
    r = db.page.update_many({}, {'$unset': {k: '' for k in fields}})
    print('%s records updated!' % r.modified_count)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
