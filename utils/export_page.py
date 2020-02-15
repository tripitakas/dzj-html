#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
from os import path, makedirs
from bson import json_util
import sys

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.page.tool import PageTool
from controller.base import prop


def export_page(db_name='tripitaka', uri='localhost', out_dir=None, source='', phonetic=False, text_finished=False):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    cond = {'source': {'$regex': str(source)}} if source else {}
    if phonetic:
        cond['$or'] = [{f: {'$regex': '音釋|音释'}} for f in ['ocr', 'ocr_col', 'text']]
    out_dir = out_dir and str(out_dir) or source or 'pages'
    for index in range(1000):
        rows = list(db.page.find(cond).skip(index * 100).limit(100))
        if rows:
            if not path.exists(out_dir):
                makedirs(out_dir)
            print('export %d pages...' % len(rows))
            for p in rows:
                if text_finished:
                    task = db.task.find_one({'task_type': {'$regex': '^text_proof'}, 'status': 'finished',
                                             'doc_id': p['name']})
                    if not task:
                        continue
                    p['text_proof'] = PageTool.html2txt(prop(task, 'result.txt_html', ''))

                p['_id'] = str(p['_id'])
                p['create_time'] = p['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                with open(path.join(out_dir, '%s.json' % str(p['name'])), 'w') as f:
                    for k, v in list(p.items()):
                        if not v or k in ['lock', 'level', 'tasks']:
                            p.pop(k)
                    f.write(json_util.dumps(p, ensure_ascii=False))


if __name__ == '__main__':
    import fire

    fire.Fire(export_page)
    print('finished!')
