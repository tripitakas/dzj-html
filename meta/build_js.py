#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pymongo
from os import path
from datetime import datetime
from functools import cmp_to_key


def update_sutra(db_name='tripitaka', uri='localhost'):
    """ 根据卷信息，更新经目信息中的起始页和终止页信息 """
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    tripitakas = ['HW', 'KB', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        print('processing %s' % tripitaka)
        sutras = list(db.sutra.find({'name': {'$regex': '^%s.*' % tripitaka}}))
        for sutra in sutras:
            reels = list(db.reel.find({'sutra_code': sutra['sutra_code'], 'reel_num': {'$ne': ''}}))
            if reels:
                reels.sort(key=cmp_to_key(lambda a, b: int(a['reel_num']) - int(b['reel_num'])))
                start_volume, start_page = reels[0]['start_volume'], reels[0]['start_page']
                end_volume, end_page = reels[-1]['end_volume'], reels[-1]['end_page']
                update = {'start_volume': start_volume, 'start_page': start_page, 'end_volume': end_volume,
                          'end_page': end_page}
                db.sutra.update_one({'sutra_code': sutra['sutra_code']}, {'$set': update})
            else:
                print('%s no reels.' % sutra['sutra_code'])


def main(db_name='tripitaka', uri='localhost'):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    base_dir = path.dirname(path.dirname(path.realpath(__file__)))
    js_dir = path.join(base_dir, 'static', 'js', 'meta')
    tripitakas = ['HW', 'KB', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        print('generating %s-sutra.js ...' % tripitaka)
        fields = dict(sutra_code=1, sutra_name=1, due_reel_count=1, existed_reel_count=1, start_volume=1, start_page=1,
                      end_volume=1, end_page=1, _id=0)
        rows = list(db.sutra.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}, fields))
        rows.sort(key=cmp_to_key(lambda a, b: int(a['sutra_code'][3:]) - int(b['sutra_code'][3:])))
        rows = [[
            r['sutra_code'][:2] + r['sutra_code'][3:].zfill(4),
            r.get('sutra_name', ''), r.get('due_reel_count', ''), r.get('existed_reel_count', ''),
            r.get('start_volume', ''), r.get('start_page', ''),
            r.get('end_volume', ''), r.get('end_page', ''),
        ] for r in rows]
        js_file = path.join(js_dir, '%s-sutra.js' % tripitaka)
        with open(js_file, 'w', encoding='utf-8') as fp:
            head = "/*\n"
            head += "* 经目信息。字段顺序依次是：\n"
            head += "* sutra_code/sutra_name/due_reel_count/existed_reel_count/start_volume/start_page/end_volume/end_page\n"
            head += "* Date: %s\n" % datetime.now().strftime('%Y-%m-%d %H:%M')
            head += "*/\n\n"
            head += "var sutras ="
            fp.write(head)
            fp.write(json.dumps(rows, ensure_ascii=False))
            fp.write(";")


if __name__ == '__main__':
    import fire

    fire.Fire(main)
