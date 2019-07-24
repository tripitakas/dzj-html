#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller.data.diff import Diff
from elasticsearch import Elasticsearch
from controller.data.variant import normalize
from controller.app import Application as App


def get_hosts():
    config = App.load_config()
    return [config.get('esearch', {})]


def can_search():
    hosts = get_hosts()
    return hosts[0].get('host')


def find(q, index='cb4ocr-ik'):
    """ 从ES中寻找与q最匹配的document """
    if not q or not can_search():
        return []

    if re.match(r'^[0-9a-zA-Z_]+', q):
        match = {'page_code': q}
    else:
        ocr = re.sub(r'[\x00-\xff]', '', q)
        ocr = re.sub(Diff.junk_cmp_str, '', ocr)
        match = {'normal': normalize(ocr)}

    dsl = {
        'query': {'match': match},
        'highlight': {'pre_tags': ['<kw>'], 'post_tags': ['</kw>'], 'fields': {'normal': {}}}
    }

    es = Elasticsearch(hosts=get_hosts())
    r = es.search(index=index, body=dsl)

    return r['hits']['hits']


def find_one(ocr, num=1):
    """ 从ES中寻找与ocr最匹配的document，返回第num个结果 """
    ret = find(ocr)
    if not ret or num - 1 not in range(0, len(ret)):
        return '', []
    hit_page_codes = [r['_source']['page_code'] for r in ret]
    cb = ''.join(ret[num - 1]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    txt = ''.join(['<kw>%s</kw>' % d['cb'] if d.get('is_same') else d['cb'] for d in diff])

    return txt, hit_page_codes


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
    print([r['_source'] for r in find('由業非以自性滅，故無賴耶亦能生', None)])
