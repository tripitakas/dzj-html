#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 根据页面的文字审定结果text字段修正回写字框的txt字段
@time: 2020-03-26
"""
import re
import pymongo
from operator import itemgetter


def main(db_name='tripitaka', uri='localhost'):
    """
    根据text字段修正回写字框的txt字段
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    """
    db = pymongo.MongoClient(uri)[db_name]
    pages = list(db.page.find({'text': {'$nin': ['', None]}}))
    print('%d pages' % len(pages))
    for page in pages:
        text_blks = re.sub('[XYMN ]', '', page['text']).split('||')

        try:
            page['columns'].sort(key=itemgetter('block_no', 'column_no'))
        except KeyError:
            for c in page['columns']:
                c['block_no'] = c.get('block_no') or int(c['column_id'][1:].split('c')[0])

        page['chars'].sort(key=itemgetter('block_no', 'column_no', 'char_no'))

        # 检查字框的列号与列框是否匹配
        column_ids = [c['column_id'] for c in page['columns']]
        column_ids_char = set([re.sub(r'c\d+$', '', c['char_id']) for c in page['chars']])
        if set(column_ids) != column_ids_char:
            print('%s column_ids mismatch: %d, %d in chars' % (page['name'], len(column_ids), len(column_ids_char)))
            continue

        # 检查文字的列与列框是否匹配
        for blk, rows in enumerate(text_blks):
            rows = rows.split('|')
            columns_blk = [c for c in column_ids if c.startswith('b%dc' % (blk + 1))]
            if len(columns_blk) != len(rows):
                print('%s.b%d columns mismatch: %d, %d rows' % (page['name'], blk + 1, len(columns_blk), len(rows)))
                continue


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished.')
