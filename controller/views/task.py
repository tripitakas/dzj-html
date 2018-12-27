#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅和我的任务
@time: 2018/12/26
"""

from tornado.web import authenticated
from controller.base import BaseHandler, DbError
import random


class ChooseCharProofHandler(BaseHandler):
    URL = ['/dzj_char.html', '/dzj_chars']

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        try:
            pages = list(self.db.cutpage.find(dict(text_lock=None)))
            random.shuffle(pages)
            tasks = [dict(name=p['name'], stage='校一', priority='高', status='待领取')
                     for p in pages[: int(self.get_argument('count', 12))]]
            self.render('dzj_char.html', tasks=tasks, count=len(pages))
        except DbError as e:
            return self.send_db_error(e)


class MyCharProofHandler(BaseHandler):
    URL = '/dzj_char_history.html'

    @authenticated
    def get(self):
        """ 我的任务-文字校对 """
        self.render('dzj_char_history.html')


class CharProofDetailHandler(BaseHandler):
    URL = ['/dzj_char_detail.html', '/dzj_char/([A-Za-z0-9_]+)']

    @authenticated
    def get(self, tid=''):
        """ 任务大厅-文字校对 """
        self.render('dzj_char_detail.html')
