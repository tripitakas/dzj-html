#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
from os import path, makedirs
from bson import json_util
import sys
from glob import glob
import json
import re

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.base import prop
from controller.page.base import PageHandler


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
                tasks = db.task.find({'doc_id': p['name'], 'task_type': {'$regex': '^text'}, 'status': 'finished'})
                if text_finished and not tasks:
                    continue
                for task in tasks:
                    p[task['task_type']] = PageHandler.html2txt(prop(task, 'result.txt_html', ''))

                p['_id'] = str(p['_id'])
                p['create_time'] = p['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                with open(path.join(out_dir, '%s.json' % str(p['name'])), 'w') as f:
                    for k, v in list(p.items()):
                        if not v or k in ['lock', 'level', 'tasks']:
                            p.pop(k)
                    f.write(json_util.dumps(p, ensure_ascii=False))


# python3 ~/export_page.py --out_dir=1200 --source=1200 --phonetic=1 --text_finished=1 --db_name=... --uri=mongodb://...
def export_phonetic(json_dir):
    with open('phonetic.txt', 'w') as f:
        for json_file in sorted(glob(path.join(json_dir, '*.json'))):
            page = json.load(open(json_file))
            texts, tags = set(), []
            for i, field in enumerate(['text_proof_1', 'text_proof_2', 'text', 'ocr', 'ocr_col']):
                text = re.search(r'(音释|音釋)\|+(.+)$', page.get(field, ''))
                if text:
                    if texts and i > 1:
                        continue
                    text = text.group(2)
                    txt2 = re.sub('[YM]', '', text)
                    if txt2 not in texts:
                        texts.add(txt2)
                        tags.append((field, text))
            names = dict(text_proof_1='一校', text_proof_2='二校', text='旧审', ocr='字框', ocr_col='行文')
            for field, text in tags:
                f.write('%s(%s)\t%s\n' % (page['name'], names[field], text))


if __name__ == '__main__':
    import fire

    fire.Fire(export_page)
    print('finished!')
