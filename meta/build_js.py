#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pymongo
from os import path
from datetime import datetime
from functools import cmp_to_key


def main(db_name='tripitaka', uri='localhost'):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    base_dir = path.dirname(path.dirname(path.realpath(__file__)))
    js_dir = path.join(base_dir, 'static', 'js', 'meta')
    tripitakas = ['GL', 'LC', 'HW', 'KB', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        print('generating %s-sutra.js ...' % tripitaka)
        fields = dict(sutra_code=1, sutra_name=1, due_reel_count=1, existed_reel_count=1, start_volume=1, start_page=1,
                      end_volume=1, end_page=1, _id=0)
        rows = list(db.sutra.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}, fields))
        rows.sort(key=cmp_to_key(lambda a, b: int(a['sutra_code'][3:]) - int(b['sutra_code'][3:])))
        rows = [[
            r.get('sutra_code', ''), r.get('sutra_name', ''), r.get('due_reel_count', ''),
            r.get('existed_reel_count', ''), r.get('start_volume', ''), r.get('start_page', ''),
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
