#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
from os import path
from tornado.options import options
from elasticsearch import Elasticsearch

BASE_DIR = path.dirname(path.dirname(path.dirname(path.dirname(__file__))))
sys.path.append(BASE_DIR)

from controller.helper import load_config
from controller.page.tool.diff import Diff
from controller.page.tool.variant import normalize


def get_hosts():
    config = load_config() or {}
    hosts = [config.get('esearch') or {'host': '47.95.216.233', 'post': 9200}]
    if hasattr(options, 'testing') and options.testing:
        hosts = [dict(host='dev.tripitakas.net')]
    return hosts


def find(q, index='cb4ocr-ik'):
    """ 从ES中寻找与q最匹配的document """
    if not q:
        return []

    if re.match(r'^[0-9a-zA-Z_]+', q):
        match = {'page_code': q}
    else:
        ocr = re.sub(r'[\x00-\xff]', '', q)
        ocr = re.sub(Diff.cmp_junk_char, '', ocr)
        match = {'normal': normalize(ocr)}

    dsl = {
        'query': {'match': match},
        'highlight': {'pre_tags': ['<kw>'], 'post_tags': ['</kw>'], 'fields': {'normal': {}}}
    }

    es = Elasticsearch(hosts=get_hosts())
    r = es.search(index=index, body=dsl)

    return r['hits']['hits']


def find_one(ocr, num=1, only_match=False):
    """ 从ES中寻找与ocr最匹配的document，返回第num个结果 """
    ocr = ''.join(ocr) if isinstance(ocr, list) else ocr.replace('|', '')
    ret = find(ocr)
    if not ret or num - 1 not in range(0, len(ret)):
        return '', []
    hit_page_codes = [r['_source']['page_code'] for r in ret]
    cb = ''.join(ret[num - 1]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    if only_match:
        # 寻找第一个和最后一个同文
        start, end = None, None
        for i, d in enumerate(diff):
            if d.get('is_same') and start is None:
                start = i
            if diff[-i - 1].get('is_same') and end is None:
                end = len(diff) - i - 1
            if start is not None and end is not None:
                break
        diff1 = diff[start: end + 1]
        # 处理diff1中前面几个异文超长的情况
        diff2 = [d for d in diff1 if not d.get('is_same')][:4]
        for d in diff2:
            if len(d.get('cb', '')) - len(d.get('ocr', '')) > 3:
                d['cb'] = d['ocr']
        txt = ''.join([d['cb'] for d in diff1])
        if end < len(diff) - 1 and not diff[end + 1].get('is_same'):
            last = diff[end + 1]
            txt += last['cb'][:len(last['ocr'])]
    else:
        txt = ''.join(['<kw>%s</kw>' % d['cb'] if d.get('is_same') else d['cb'] for d in diff])
    return txt.strip('\n'), hit_page_codes


def find_neighbor(page_code, neighbor='next'):
    """ 从ES中寻找page_code的前一页或后一页记录 """
    assert neighbor in ['prev', 'next']
    head = re.search(r'^([A-Z]{1,2}\d+n[A-Z]?\d+[A-Za-z_]?)p([a-z]?\d+)', page_code)
    page_no = head.group(2)
    neighbor_no = str(int(page_no) + 1 if neighbor == 'next' else int(page_no) - 1).zfill(len(page_no))
    neighbor_code = '%sp%s' % (head.group(1), neighbor_no)
    neighbor_node = find(neighbor_code)
    return neighbor_node and neighbor_node[0]


if __name__ == '__main__':
    import pymongo

    # print([r['_source'] for r in find('由業非以自性滅，故無賴耶亦能生')])
    local_db = pymongo.MongoClient('mongodb://localhost')['tripitaka']
    page = local_db.page.find_one({'name': 'GL_1047_1_11'}, {'ocr': 1})
    ocr1 = page['ocr']
    ocr1 = re.sub(r'[■\|]', '', ocr1)
    txt1 = find_one(ocr1, only_match=True)[0]
    print(txt1)
