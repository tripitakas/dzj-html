#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
from bson import json_util
from os import path, makedirs


def export_page(db_name='tripitaka', uri='localhost', out_dir=None, source=''):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    cond = {'source': source} if source else {}
    for index in range(1000):
        rows = list(db.page.find(cond).skip(index * 100).limit(100))
        if rows:
            out_dir = out_dir or source or 'pages'
            if not path.exists(out_dir):
                makedirs(out_dir)
            print('export %d pages...' % len(rows))
            for p in rows:
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
