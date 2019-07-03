#!/usr/bin/env python
# -*- coding: utf-8 -*-
# nohup python3 /home/sm/tripitakas/controller/cbeta.py >> /home/sm/cbeta/cbeta.log 2>&1 &

import re
import sys
from os import path
from glob2 import glob
from datetime import datetime
from functools import partial
from controller.data.variant import normalize
from controller.data.rare import format_rare

sys.path.append(path.dirname(path.dirname(__file__)))  # to use controller

from controller.data.diff import Diff
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException

BM_PATH = r'/home/sm/cbeta/BM_u8'


def scan_txt(add, root_path):
    def add_page():
        if rows:
            try:
                page_code = '%sn%sp%s' % (volume_no, book_no, page_no)
                origin = [format_rare(r) for r in rows]
                normal = [normalize(r) for r in origin]
                add(body=dict(page_code=page_code, volume_no=volume_no, book_no=book_no, page_no=page_no,
                              origin=origin, normal=normal, updated_time=datetime.now()))
                print('processing %d file: %s\t%s\t%d lines' % (i + 1, page_code, fn, len(normal)))
            except ElasticsearchException as e:
                sys.stderr.write('fail to process file\t%d: %s\t%d lines\t%s\n' % (i + 1, fn, len(rows), str(e)))

    volume_no = book_no = page_no = None  # 册号，经号，页码
    rows, last_rows = [], []
    for i, fn in enumerate(sorted(glob(path.join(root_path, '**',  r'new.txt')))):
        with open(fn, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for row in lines:
            texts = re.split('#{1,3}', row.strip(), 1)
            if len(texts) != 2:
                continue
            head = re.search(r'^([A-Z]{1,2}\d+)n(\d+)[A-Za-z_]p(\d+)([abcd]\d+)', texts[0])
            if head:
                volume, book, page = head.group(1), int(head.group(2)), int(head.group(3))
                if [volume_no, book_no, page_no] != [volume, book, page]:
                    add_page()
                    volume_no, book_no, page_no = volume, book, page
                    rows, last_rows = [], rows
            content = re.sub(r'\[.>(.)\]', lambda m: m.group(1), texts[1])
            content = re.sub(r'(<[\x00-\xff]*?>|\[[\x00-\xff＊]*\])', '', content)
            rows.append(content)
    add_page()


def build_db(index='cbeta4ocr', root_path=None, jieba=False):
    es = Elasticsearch()
    es.indices.delete(index=index, ignore=[400, 404])
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

    scan_txt(partial(es.index, index=index, ignore=[400, 404]), root_path or BM_PATH)


def pre_filter(txt):
    return re.sub('[\x00-\xff]', '', txt)


def find(ocr):
    if not ocr:
        return []
    match = {'page_code': ocr.replace('_', '')} if re.match(r'^[0-9a-zA-Z_]+', ocr) else {'rows': pre_filter(ocr)}
    dsl = {
        'query': {'match': match},
        'highlight': {
            'pre_tags': ['<kw>'],
            'post_tags': ['</kw>'],
            'fields': {'rows': {}}
        }
    }
    host = [dict(host='47.95.216.233', port=9200), dict(host='localhost', port=9200)]
    es = Elasticsearch(hosts=host)
    r = es.search(index='cbeta4ocr', body=dsl)
    return r['hits']['hits']


def _find_one(ocr):
    r = find(ocr)
    if not r:
        return ''
    cb_doc = ''.join(r[0]['_source']['rows'])
    ret = Diff.diff(ocr, cb_doc, label=dict(base='ocr', cmp1='cbeta'))[0]
    is_same = [k for k, v in enumerate(ret) if v.get('is_same')]
    ret[is_same[0]]['cbeta'] = '<start>' + ret[is_same[0]]['cbeta']
    ret[is_same[-1]]['cbeta'] = ret[is_same[-1]]['cbeta'] + '<end>'
    cb_doc = ''.join([r['cbeta'] for r in ret])
    return cb_doc


def find_one(ocr):
    r = find(ocr)
    if not r:
        return ''
    cb_doc = ''.join(r[0]['_source']['rows'])
    ret = Diff.diff(ocr, cb_doc, label=dict(base='ocr', cmp1='cbeta'))[0]
    is_same = [k for k, v in enumerate(ret) if v.get('is_same')]
    ret[is_same[0]]['cbeta'] = '<start>' + ret[is_same[0]]['cbeta']
    ret[is_same[-1]]['cbeta'] = ret[is_same[-1]]['cbeta'] + '<end>'
    r = ''.join([r['cbeta'] for r in ret])

    # 如果第一段异文中ocr失配的长度超过10，则重新检索
    if not ret[0]['is_same'] and len(ret[0]['ocr']) > 10:
        r = _find_one(ret[0]['ocr']) + r'\n' + r

    # 如果最后一段异文中ocr失配的长度超过10，则重新检索
    if not ret[-1]['is_same'] and len(ret[-1]['ocr']) > 10:
        r = r + r'\n' + _find_one(ret[-1]['ocr'])

    return r


if __name__ == '__main__':
    import fire

    fire.Fire(build_db)
