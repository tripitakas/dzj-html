#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
import re
from bson import json_util
from controller.base import BaseHandler
from controller.page.tool.esearch import find
from controller.page.tool.variant import normalize
from controller.helper import prop


def punc_str(orig_str, host):
    import requests
    import logging
    try:
        res = requests.get("http://%s:10888/seg" % (host,), params={'q': orig_str}, timeout=0.1)
    except Exception as e:
        logging.error(str(e))
        return orig_str

    return res.text


class PunctuationApi(BaseHandler):
    URL = '/api/com/punctuate'

    def post(self):
        """ 自动标点"""
        try:
            q = self.data.get('q', '').strip()
            res = punc_str(q, prop(self.config, 'punctuate.host', 'localhost')) if q else ''
            self.send_data_response(dict(res=res))

        except self.DbError as error:
            return self.send_db_error(error)


class CbetaSearchApi(BaseHandler):
    URL = '/api/com/search'

    def post(self):
        """ CBETA检索"""

        def merge_kw(txt):
            # 将<kw>一</kw>，<kw>二</kw>格式替换为<kw>一，二</kw>
            regex = r'[，、：；。？！“”‘’「」『』（）%&*◎—……]+'
            txt = re.sub('</kw>(%s)<kw>' % regex, lambda r: r.group(1), txt)
            # 合并相邻的关键字
            txt = re.sub('</kw><kw>', '', txt)
            return txt

        q = self.data.get('q', '').strip()
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


class SessionConfigApi(BaseHandler):
    URL = '/api/session/config'

    def post(self):
        """ 配置后台cookie"""
        blacklist = ['user']
        try:
            for k, v in self.data.items():
                assert k not in blacklist
                self.set_secure_cookie(k, json_util.dumps(v))
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
