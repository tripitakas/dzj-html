#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/08/16
"""
import re
from .esearch import find
from controller.base import BaseHandler
from controller.text.variant import normalize


class CbetaSearchApi(BaseHandler):
    URL = '/api/search/cbeta'

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
