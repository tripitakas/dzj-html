#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅和我的任务
@time: 2018/12/26
"""

from tornado.web import authenticated
from controller.base import BaseHandler, DbError, convert_bson
import random


class ChooseCutProofHandler(BaseHandler):
    URL = ['/dzj_slice.html', '/dzj_cut']

    @authenticated
    def get(self):
        """ 任务大厅-切分校对 """
        try:
            # 查找未领取或自己未完成的页面，自己未完成的页面显示在前面
            pages = list(self.db.cutpage.find({
                '$or': [{'cut_lock_user': None}, {'cut_lock_user': self.current_user.id}],
                'text_status': None  # 未完成，后续应改为待领取状态
            }))
            random.shuffle(pages)
            pages = [p for p in pages if p.get('cut_lock_user')] + [p for p in pages if not p.get('cut_lock_user')]

            tasks = [dict(name=p['name'], kind='字切分', priority='高',
                          status='待继续' if p.get('cut_lock_user') else '待领取')
                     for p in pages[: int(self.get_argument('count', 12))]]
            self.render('dzj_slice.html', tasks=tasks, remain=len(pages))
        except DbError as e:
            return self.send_db_error(e)


class ChooseCharProofHandler(BaseHandler):
    URL = ['/dzj_char.html', '/dzj_chars']

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        try:
            # 查找未领取或自己未完成的页面
            pages = list(self.db.cutpage.find({
                '$or': [{'text_lock_user': None}, {'text_lock_user': self.current_user.id}],
                'text_status': None  # 未完成，后续应改为待领取状态
            }))
            random.shuffle(pages)
            pages = [p for p in pages if p.get('text_lock_user')] + [p for p in pages if not p.get('text_lock_user')]

            tasks = [dict(name=p['name'], stage='校一', priority='高',
                          status='待继续' if p.get('text_lock_user') else '待领取')
                     for p in pages[: int(self.get_argument('count', 12))]]
            self.render('dzj_char.html', tasks=tasks, remain=len(pages))
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
    def get(self, name=''):
        """ 进入文字校对 """
        try:
            page = convert_bson(self.db.cutpage.find_one(dict(name=name)))
            if not page:
                return self.render('_404.html')
            self.render('dzj_char_detail.html', page=page,
                        readonly=page.get('text_lock_user') != self.current_user.id)
        except DbError as e:
            return self.send_db_error(e)
