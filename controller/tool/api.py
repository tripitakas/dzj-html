#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/08/16
"""
import re
import json
import logging
import subprocess
from PIL import Image
from .esearch import find
from os import path, remove
from controller import helper
from urllib.parse import urlencode
from controller.helper import prop
from controller import errors as e
from tornado.escape import to_basestring
from controller.text.variant import normalize
from controller.base import BaseHandler, DbError

try:
    import punctuation

    punc_str = punctuation.punc_str
except Exception:
    punc_str = lambda s: s


class PunctuationApi(BaseHandler):
    URL = '/api/tool/punctuate'

    def post(self):
        """ 自动标点 """
        try:
            data = self.get_request_data()
            q = data.get('q', '').strip()
            res = punc_str(q) if q else ''
            self.send_data_response(dict(res=res))

        except DbError as error:
            return self.send_db_error(error)


class CbetaSearchApi(BaseHandler):
    URL = '/api/tool/search'

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
        except Exception as error:
            matches = [dict(hits=[str(error)])]

        for m in matches:
            try:
                highlights = {re.sub('</?kw>', '', v): merge_kw(v) for v in m['highlight']['normal']}
                hits = [highlights.get(normalize(r), r) for r in m['_source']['origin']]
                m['hits'] = hits
            except KeyError:
                m['hits'] = m.get('hits') or m['_source']['origin']

        self.send_data_response(dict(matches=matches))
