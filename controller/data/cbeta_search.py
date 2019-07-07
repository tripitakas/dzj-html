#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller.data.diff import Diff
from controller.data.variant import normalize
from elasticsearch import Elasticsearch


def find(ocr, node, index='cb4ocr-ik'):
    """ 从ES中寻找与ocr最匹配的document
    :param ocr: ocr文本或者page_code
    :param node: cbeta全文库配置
    :param index: 'cb4ocr-ik'或'cbeta4ocr'
    """
    if not ocr:
        return []

    if re.match(r'^[0-9a-zA-Z_]+', ocr):
        match = {'page_code': ocr}
    else:
        ocr = re.sub(r'[\x00-\xff]', '', ocr)
        ocr = re.sub(Diff.junk_cmp_str, '', ocr)
        match = {'normal': normalize(ocr)}

    dsl = {
        'query': {'match': match},
        'highlight': {
            'pre_tags': ['<kw>'],
            'post_tags': ['</kw>'],
            'fields': {'normal': {}}
        }
    }

    host = ([node] if node else []) + [dict(host='localhost', port=9200)]
    es = Elasticsearch(hosts=host)
    r = es.search(index=index, body=dsl)

    return r['hits']['hits']


def find_one(ocr, node):
    r = find(ocr, node)
    if not r:
        return ''
    cb = ''.join(r[0]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    r = ''.join([
        '<kw>%s</kw>' % d['cb'] if d.get('is_same') else d['cb']
        for d in diff
    ])
    return r


if __name__ == '__main__':
    find('由業非以自性滅，故無賴耶亦能生', None)
