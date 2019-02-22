#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅和我的任务
@time: 2018/12/26
"""

from tornado.web import authenticated
from controller.base import BaseHandler, DbError, convert_bson
import random
import re
import model.user as u


def get_my_or_free_tasks(self, task_type, max_count=12):
    """ 查找未领取或自己未完成的任务 """
    assert re.match(u.re_task_type, task_type)
    task_user = task_type + '_user'
    pages = list(self.db.page.find({
        '$or': [{task_user: None}, {task_user: self.current_user.id}],
        task_type + '_status': None  # 未完成，后续应改为待领取状态
    }))
    random.shuffle(pages)
    pages = [p for p in pages if p.get(task_user)] + [p for p in pages if not p.get(task_user)]
    return pages, pages[: int(self.get_argument('count', max_count))]


def get_my_tasks(self, task_type, cond=None):
    """ 查找自己领取的任务 """
    assert re.match(u.re_task_type, task_type)
    cond = {task_type + '_status': None} if cond is None else cond
    cond[task_type + '_user'] = self.current_user.id
    return list(self.db.page.find(cond))


class ChooseCutProofHandler(BaseHandler):
    URL = ['/dzj_slice.html', '/dzj_cut']

    @authenticated
    def get(self):
        """ 任务大厅-切分校对 """
        try:
            pages, tasks = get_my_or_free_tasks(self, 'cut_proof')
            tasks = [dict(name=p['name'], kind='字切分', priority='高',
                          status='待继续' if p.get('cut_proof_user') else '待领取') for p in tasks]
            self.render('dzj_slice.html', tasks=tasks, remain=len(pages))
        except DbError as e:
            return self.send_db_error(e)


class ChooseCharProofHandler(BaseHandler):
    URL = ['/dzj_char.html', '/dzj_chars']

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        try:
            pages, tasks = get_my_or_free_tasks(self, 'text_proof')
            tasks = [dict(name=p['name'], stage='校一', priority='高',
                          status='待继续' if p.get('text_proof_user') else '待领取') for p in tasks]
            self.render('dzj_char.html', tasks=tasks, remain=len(pages))
        except DbError as e:
            return self.send_db_error(e)


class MyTasksHandler(BaseHandler):
    URL = '/dzj_([a-z_]+)_history.html'

    @authenticated
    def get(self, kind):
        """ 我的任务 """
        try:
            task_types = dict(char='text_proof', char_check='text_review',
                              hard='hard_proof', hard_check='hard_review',
                              slice='cut_proof', slice_check='cut_review',
                              fmt='fmt_proof', fmt_check='fmt_review')
            assert kind in task_types
            task_type = task_types[kind]
            pages = get_my_tasks(self, task_type, {})
            self.render('dzj_{}_history.html'.format(kind), pages=pages, task_type=task_type)
        except DbError as e:
            return self.send_db_error(e)


class CharProofDetailHandler(BaseHandler):
    URL = ['/dzj_char_detail.html', '/dzj_char/([A-Za-z0-9_]+)']

    @authenticated
    def get(self, name=''):
        """ 进入文字校对 """
        try:
            page = convert_bson(self.db.page.find_one(dict(name=name))) or dict(name='?')
            if not page:
                return self.render('_404.html')
            self.render('dzj_char_detail.html', page=page,
                        readonly=page.get('text_proof_user') != self.current_user.id)
        except DbError as e:
            return self.send_db_error(e)
