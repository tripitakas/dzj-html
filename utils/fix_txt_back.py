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
    changed = 0
    for page in pages:
        try:
            page['columns'].sort(key=itemgetter('block_no', 'column_no'))
        except KeyError:
            for c in page['columns']:
                c['block_no'] = c.get('block_no') or int(c['column_id'][1:].split('c')[0])

        page['chars'].sort(key=itemgetter('block_no', 'column_no', 'char_no'))

        r = fix_page(page, page['text'], not page.get('text_proof_1'))
        if r == -1 and page.get('text_proof_1'):
            r = fix_page(page, page.get('text_proof_1'), True)
        if r > 0:
            r = db.page.update_one({'name': page['name']}, {'$set': {'chars': page['chars']}})
            if r.modified_count:
                changed += 1
    print('%d page changed' % changed)


def fix_page(page, text, prompt):
    text_blks = re.sub('[XYMN　 ]', '', text).split('||')
    changed, has_err = 0, False

    # 检查字框的列号与列框是否匹配
    column_ids = [c['column_id'] for c in page['columns']]
    column_ids_char = set([re.sub(r'c\d+$', '', c['char_id']) for c in page['chars']])
    if set(column_ids) != column_ids_char:
        if prompt:
            print('E %s column_ids mismatch: %d, %d in chars' % (page['name'], len(column_ids), len(column_ids_char)))
        return -1

    # 检查文字的列与列框是否匹配
    for blk, rows in enumerate(text_blks):
        rows = rows.split('|')
        columns_blk = [c for c in column_ids if c.startswith('b%dc' % (blk + 1))]
        if len(columns_blk) != len(rows):
            if prompt:
                print('E %s.b%d columns mismatch: %d, %d rows' % (page['name'], blk + 1, len(columns_blk), len(rows)))
            has_err = True
            continue

        for i, (col_id, text) in enumerate(zip(columns_blk, rows)):
            chars = [c for c in page['chars'] if c['char_id'].startswith(col_id + 'c')]
            old_text = ''.join(c.get('txt') or '?' for c in chars)
            if len(chars) != len(text):
                print('W %s %s chars mismatch: %d boxes, %d chars, %s : %s' % (
                    page['name'], col_id, len(chars), len(text), old_text, text))
                for c in chars:
                    if c.get('ocr_txt'):
                        if c.get('txt') != c.get('ocr_txt'):
                            changed += 1
                        c['txt'] = c['ocr_txt']
            else:
                for c, txt in zip(chars, text):
                    if c.get('txt') != txt:
                        changed += 1
                    c['txt'] = txt
            new_text = ''.join(c.get('txt') or '?' for c in chars)
            if old_text != new_text:
                print('I %s %s chars changed: %s -> %s' % (page['name'], col_id, old_text, new_text))

    return changed or (-1 if has_err else 0)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished.')
