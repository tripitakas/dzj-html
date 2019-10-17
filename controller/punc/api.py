#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/08/16
"""
from controller.base import BaseHandler, DbError

try:
    import punctuation

    punc_str = punctuation.punc_str
except Exception:
    punc_str = lambda s: s


class PunctuationApi(BaseHandler):
    URL = '/api/punctuate'

    def post(self):
        """ 自动标点 """
        try:
            data = self.get_request_data()
            q = data.get('q', '').strip()
            res = punc_str(q) if q else ''
            self.send_data_response(dict(res=res))

        except DbError as e:
            return self.send_db_error(e)
