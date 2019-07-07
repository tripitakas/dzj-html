#!/usr/bin/env python
# -*- coding: utf-8 -*-
# nohup python3 /home/sm/tripitakas/controller/data/cbeta_build.py >> /home/sm/cbeta/cbeta.log 2>&1 &
# python3 controller/data/cbeta_build.py --bm_path=BM_u8_path
#
# 查看实际导入的数量: curl 'localhost:9200/_cat/indices?v'
# 查看最近导入的日志: python3 -c "print(''.join(open('/home/sm/cbeta/cbeta.log').readlines()[-5:]))"

import re
import sys
import json
from os import path
from glob2 import glob
from datetime import datetime
from functools import partial

sys.path.append(path.dirname(path.dirname(path.dirname(__file__))))  # to use controller

from controller.data.variant import normalize
from controller.data.rare import format_rare
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchException

BM_PATH = '/home/sm/cbeta/BM_u8'  # BM_u8所在路径，可在本文件的bm_path参数动态指定
re_head_parts = re.compile(r'^([A-Z]{1,2}\d+)n([A-Z]?\d+)[A-Za-z_]?p([a-z]?\d+)')


def junk_filter(txt):
    txt = re.sub('<.*?>', '', txt)
    txt = re.sub(r'\[.>(.)\]', lambda m: m.group(1), txt)
    txt = re.sub(r'\[[\x00-\xff＊]*\]', '', txt)
    return txt


def cur_time():
    return datetime.now().strftime('[%H:%M:%S]')


def add_page(index, rows, page_code):
    if rows:
        origin = [format_rare(r) for r in rows]
        normal = [normalize(r) for r in origin]
        count = sum(len(r) for r in normal)
        if count > 15000 or len(origin) > 5000:  # 跳过大文件
            sys.stderr.write('%s\tfailed:\t%s\t%s lines\t %s chars\tout of limit\n' % (
                cur_time(), page_code, len(rows), len(origin)))
            return False

        volume_no = book_no = page_no = None  # 册号，经号，页码
        head = re_head_parts.search(page_code)
        if head:
            volume_no, book_no, page_no = head.group(1), head.group(2), head.group(3)

        try:
            index(body=dict(
                page_code=page_code, volume_no=volume_no, book_no=book_no, page_no=page_no,
                origin=origin, normal=normal, lines=len(rows), char_count=count, updated_time=datetime.now())
            )
            print('%s\tsuccess:\t%s\t%s lines\t %s chars' % (cur_time(), page_code, len(rows), len(origin)))
            return True
        except ElasticsearchException as e:
            sys.stderr.write('%s\tfailed:\t%s\t%s lines\t %s chars\t%s\n' % (
                cur_time(), page_code, len(rows), len(origin), str(e)))
            return False


def scan_and_index_dir(index, source):
    """直接导入目录中的文本数据"""
    rows, errors, page_code = [], [], None
    for i, fn in enumerate(sorted(glob(path.join(source, '**', r'new.txt')))):
        print('processing file %s' % fn)
        with open(fn, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for row in lines:
            texts = re.split('#{1,3}', row.strip(), 1)
            if len(texts) != 2:
                continue
            head = re_head_parts.search(texts[0])
            if head:
                if page_code and page_code != head.group(0):
                    if not add_page(index, rows, page_code):
                        errors.append(page_code)
                    rows = []
                page_code = head.group(0)
            else:
                print('head error:\t%s' % row)
            rows.append(junk_filter(texts[1]))
    if not add_page(index, rows, page_code):
        errors.append(page_code)

    if errors:
        with open(path.join(source, datetime.now().strftime('error-%Y%m%d-%H%M.json')), 'w') as f:
            json.dump(errors, f)
        print('%s error pages\n%s' % (len(errors), errors))


def index_page_codes(index, fn, base_dir):
    """根据json文件中指定的page_code页码重新导入"""
    with open(fn, 'r', encoding='utf-8') as f:
        page_codes = json.load(f)
    errors = []
    for page_code in page_codes:
        head = re.search(r'^([A-Z]{1,2})(\d+)n([A-Z]?\d+)[A-Za-z_]?p([a-z]?\d+)', page_code)
        from_file = path.join(base_dir, head.group(1), head.group(1) + head.group(2), 'new.txt')
        with open(from_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        rows = [junk_filter(re.split('#{1,3}', line.strip(), 1)[1]) for line in lines if page_code in line]
        if not add_page(index, rows, page_code):
            errors.append(page_code)

    if errors:
        with open(path.join(path.basename(fn), datetime.now().strftime('error-%Y%m%d-%H%M.json'))) as f:
            json.dump(errors, f)
        print('%s error pages\n%s' % (len(errors), errors))


def build_db(index='cb4ocr-ik', source='default', bm_path=BM_PATH, mode='create', split='ik'):
    """ 基于CBETA文本创建索引，以便ocr寻找比对文本使用
    :param index: 索引名称
    :param source: 待加工的数据来源，有两种：
            1.目录(default)：这种情况下直接导入目录中的文本数据
            2.json文件名：这种情况下根据json文件中指定的page_code页码重新导入，txt目录可在bm_path参数指定
    :param bm_path: BM_u8文本目录
    :param mode: 'create'表示新建，'update'表示更新
    :param split: 中文分词器的名称，如'ik'或'jieba'
    """
    es = Elasticsearch()

    if mode == 'create':
        es.indices.delete(index=index, ignore=[400, 404])
        es.indices.create(index=index, ignore=400)
    else:
        es.indices.open(index=index, ignore=400)

    if split == 'ik':
        mapping = {'properties': {
            'normal': {'type': 'text', 'analyzer': 'ik_max_word', 'search_analyzer': 'ik_smart'},
            'origin': {'type': 'text', 'analyzer': 'ik_max_word', 'search_analyzer': 'ik_smart'},
        }}
        es.indices.put_mapping(index=index, body=mapping)
    elif split == 'jieba':
        mapping = {'properties': {
            'normal': {'type': 'text', 'analyzer': 'jieba_index', 'search_analyzer': 'jieba_index'},
            'origin': {'type': 'text', 'analyzer': 'jieba_index', 'search_analyzer': 'jieba_index'},
        }}
        es.indices.put_mapping(index=index, body=mapping)

    if '.json' in source:
        index_page_codes(partial(es.index, index=index, ignore=[]), source, bm_path)
    else:
        scan_and_index_dir(partial(es.index, index=index, ignore=[]), bm_path)


if __name__ == '__main__':
    import fire

    fire.Fire(build_db)
