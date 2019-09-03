#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/08/16
"""
import re
from controller.data.esearch import find
from controller.data.variant import normalize
from controller.base import BaseHandler, DbError

try:
    import punctuation

    puncstr = punctuation.punc_str
except Exception:
    puncstr = lambda s: s


class CbetaSearchApi(BaseHandler):
    URL = '/api/data/cbeta/search'

    def post(self):
        """ CBETA检索 """

        def merge_kw(txt):
            # 将<kw>一</kw>，<kw>二</kw>格式替换为<kw>一，二</kw>
            regex = r'[，、：；。？！“”‘’「」『』（）%&*◎—……]+'
            txt = re.sub('</kw>(%s)<kw>' % regex, lambda r: r.group(1), txt)
            # 合并相邻的关键字
            txt = re.sub('</kw><kw>', '', txt)
            return txt

        data = self.get_request_data()
        q = data.get('q', '').strip()
        try:
            matches = find(q)
        except Exception as e:
            matches = [dict(hits=[str(e)])]

        for m in matches:
            try:
                highlights = {re.sub('</?kw>', '', v): merge_kw(v) for v in m['highlight']['normal']}
                hits = [highlights.get(normalize(r), r) for r in m['_source']['origin']]
                m['hits'] = hits
            except KeyError:
                m['hits'] = m.get('hits') or m['_source']['origin']

        self.send_data_response(dict(matches=matches))


class PunctuationApi(BaseHandler):
    URL = '/api/data/punctuation'

    def post(self):
        """ 自动标点 """
        try:
            data = self.get_request_data()
            q = data.get('q', '').strip()
            res = puncstr(q) if q else ''
            self.send_data_response(dict(res=res))

        except DbError as e:
            return self.send_db_error(e)
