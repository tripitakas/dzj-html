#!/usr/bin/env python
# -*- coding: utf-8 -*-
# nohup python3 /home/sm/tripitakas/controller/data/cbeta.py >> /home/sm/cbeta/cbeta.log 2>&1 &
# nohup python3 /home/sm/tripitakas/controller/data/cbeta.py --only_missing=1 >> /home/sm/cbeta/cbeta.log 2>&1 &

import re
import sys
from os import path
from glob2 import glob
from datetime import datetime
from functools import partial

sys.path.append(path.dirname(path.dirname(path.dirname(__file__))))  # to use controller

from controller.data.diff import Diff
from controller.data.variant import normalize
from controller.data.rare import format_rare
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException

BM_PATH = '/home/sm/cbeta/BM_u8'
errors = []
success = []


def scan_txt(add, root_path, only_missing, exist_ids):
    def add_page():
        if rows:
            page_code = '%sn%sp%s' % (volume_no, book_no, page_no)
            if only_missing and page_code not in only_missing or page_code in exist_ids:
                return
            if len(rows) > 5000 or sum(len(r) for r in rows) > 20000:
                errors.append('%s\t%d\t%d\t%s\n' % (page_code, i + 1, len(rows), 'out of limit'))
                large_file = path.join(path.dirname(root_path), page_code + '.txt')
                if not path.exists(large_file):
                    with open(large_file, 'w') as tf:
                        tf.write('\n'.join(rows))
                return
            if errors and 'AuthorizationException' in errors[-1]:
                errors.append('%s\t%d\t%d\n' % (page_code, i + 1, len(rows)))
                return
            try:
                origin = [format_rare(r) for r in rows]
                normal = [normalize(r) for r in origin]
                count = sum(len(r) for r in normal)
                if add:
                    add(body=dict(page_code=page_code, volume_no=volume_no, book_no=book_no, page_no=page_no,
                                  origin=origin, normal=normal, lines=len(normal), char_count=count,
                                  updated_time=datetime.now()))
                    success.append(page_code)
                    print('[%s] file %d:\t%s\t%-3d lines\t%-4d chars' % (
                        datetime.now().strftime('%d%H:%M:%S'), i + 1, page_code, len(normal), count))
            except ElasticsearchException as e:
                errors.append('%s\t%d\t%d\t%s\n' % (page_code, i + 1, len(rows), str(e)))
                sys.stderr.write('fail to process file\t%d: %s\t%d lines\t%s\n' % (i + 1, fn, len(rows), str(e)))

    def in_missing(prefix):
        return [p for p in only_missing if prefix in p]

    volume_no = book_no = page_no = None  # 册号，经号，页码
    rows, last_rows = [], []
    unknown_heads = []

    for i, fn in enumerate(sorted(glob(path.join(root_path, '**', r'new.txt')))):
        if only_missing and not in_missing(path.basename(path.dirname(fn)) + 'n'):
            continue
        with open(fn, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for row in lines:
            texts = re.split('#{1,3}', row.strip(), 1)
            if len(texts) != 2:
                continue
            head = re.search(r'^([A-Z]{1,2}\d+)n(A?\d+)[A-Za-z_]?p(\d+)', texts[0])
            if not head and re.match(r'^([A-Z]{1,2}\d+)n', texts[0]):
                if texts[0] not in unknown_heads:
                    unknown_heads.append(texts[0])
                    sys.stderr.write('unknown head: %s in %s\n' % (texts[0], fn))
            if head:
                volume, book, page = head.group(1), int(head.group(2).replace('A', '')), int(head.group(3))
                if [volume_no, book_no, page_no] != [volume, book, page]:
                    add_page()
                    volume_no, book_no, page_no = volume, book, page
                    rows, last_rows = [], rows
            content = re.sub(r'\[.>(.)\]', lambda m: m.group(1), texts[1])
            content = re.sub(r'(<[\x00-\xff]*?>|\[[\x00-\xff＊]*\])', '', content)
            rows.append(content)
    add_page()
    print('%d pages added, %d pages failed' % (len(success), len(errors)))
    if success:
        with open(path.join(path.dirname(root_path), 'bm_err.log'), 'w') as f:
            f.writelines(errors)


def build_db(index='cbeta4ocr', root_path=None, jieba=False, only_missing=False):
    es = index and Elasticsearch()
    ids_file = path.join(root_path or BM_PATH, 'exist_ids.txt')
    exist_ids = []
    if path.exists(ids_file):
        with open(ids_file) as f:
            exist_ids = f.read().split('\n')
    if es:
        if not only_missing and not exist_ids:
            es.indices.delete(index=index, ignore=[400, 404])
        else:
            try:
                with open(path.join(path.dirname(root_path or BM_PATH), 'bm_err.log')) as f:
                    only_missing = [t.split('\t')[0] for t in f.readlines()]
            except OSError:
                only_missing = []
            print('last missing %d pages' % len(only_missing))
        es.indices.create(index=index, ignore=400)
        if jieba:
            mapping = {
                'properties': {
                    'rows': {
                        'type': 'text',
                        'analyzer': 'jieba_index',
                        'search_analyzer': 'jieba_index'
                    }
                }
            }
            es.indices.put_mapping(index=index, body=mapping)

    scan_txt(es and partial(es.index, index=index, ignore=[400, 404]), root_path or BM_PATH,
             only_missing, exist_ids)


def pre_filter(txt):
    txt = re.sub(r'[\x00-\xff]', '', txt)
    txt = re.sub(Diff.junk_cmp_str, '', txt)
    return txt


def find(ocr):
    if not ocr:
        return []

    match = {'normal': normalize(pre_filter(ocr))}
    if re.match(r'^[0-9a-zA-Z_]+', ocr):
        match = {'page_code': ocr.replace('_', '')}
    dsl = {
        'query': {'match': match},
        'highlight': {
            'pre_tags': ['<kw>'],
            'post_tags': ['</kw>'],
            'fields': {'normal': {}}
        }
    }
    host = [dict(host='47.95.216.233', port=9200), dict(host='localhost', port=9200)]
    es = Elasticsearch(hosts=host)
    r = es.search(index='cbeta4ocr', body=dsl)
    return r['hits']['hits']


def find_one(ocr):
    r = find(ocr)
    if not r:
        return ''
    cb = ''.join(r[0]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    r = ''.join([
        '<kw>%s</kw>' % pre_filter(d['cb']) if d.get('is_same') else pre_filter(d['cb'])
        for d in diff
    ])
    return r


if __name__ == '__main__':
    import fire

    fire.Fire(build_db)
