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
    task_status = task_type + '_status'
    pages = list(self.db.page.find({
        '$or': [
            {task_user: None, '$or': [{task_status: u.STATUS_OPENED}, {task_status: u.STATUS_RETURNED}]},
            {task_user: self.current_user.id, task_status: u.STATUS_LOCKED}],
    }))

    # 交叉审核、背靠背校对
    if task_type == 'text2_proof':
        pages = [p for p in pages if p.get('text1_proof_user') != self.current_user.id]
    elif task_type == 'text3_proof':
        pages = [p for p in pages if p.get('text1_proof_user') != self.current_user.id and
                 p.get('text2_proof_user') != self.current_user.id]
    elif task_type == 'text_review':
        pages = [p for p in pages if p.get('text1_proof_user') != self.current_user.id and
                 p.get('text2_proof_user') != self.current_user.id and
                 p.get('text3_proof_user') != self.current_user.id]
    elif 'review' in task_type:
        pages = [p for p in pages if p.get(task_user.replace('review', 'proof')) != self.current_user.id]

    random.shuffle(pages)
    pages = [p for p in pages if p.get(task_user)] + [p for p in pages if not p.get(task_user)]
    return pages, pages[: int(self.get_argument('count', max_count))]


def get_my_tasks(self, task_type, cond=None):
    """ 查找自己领取的任务 """
    assert re.match(u.re_task_type, task_type)
    cond = {task_type + '_status': u.STATUS_OPENED} if cond is None else cond
    cond[task_type + '_user'] = self.current_user.id
    return list(self.db.page.find(cond))


class ChooseCutProofHandler(BaseHandler):
    URL = '/dzj_slice.html'

    @authenticated
    def get(self):
        """ 任务大厅-切分校对 """
        try:
            all_pages, all_tasks = [], []
            for task_type in ['block_cut_proof', 'column_cut_proof', 'char_cut_proof']:
                pages, tasks = get_my_or_free_tasks(self, task_type)
                task_name = '切%s' % (dict(block='栏', column='列', char='字')[task_type.split('_')[0]],)
                tasks = [dict(name=p['name'], priority='高', kind=task_name,
                              status='待继续' if p.get(task_type + '_user') else
                              u.task_statuses.get(p.get(task_type + '_status')) or '待领取') for p in tasks]
                all_pages.extend(pages)
                all_tasks.extend(tasks)
            self.render('dzj_slice.html', tasks=all_tasks, remain=len(all_pages))
        except DbError as e:
            return self.send_db_error(e)


class ChooseCharProofHandler(BaseHandler):
    URL = ['/dzj_char.html', '/dzj_chars']

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        try:
            stage, field = '校一', 'text1'
            pages, tasks = get_my_or_free_tasks(self, 'text1_proof')
            if not tasks:
                pages, tasks = get_my_or_free_tasks(self, 'text2_proof')
                stage, field = '校二', 'text2'
            if not tasks:
                pages, tasks = get_my_or_free_tasks(self, 'text3_proof')
                stage, field = '校三', 'text3'
            tasks = [dict(name=p['name'], stage=stage, priority='高', proof_field=field,
                          status='待继续' if p.get(field + '_proof_user') else '待领取') for p in tasks]
            self.render('dzj_char.html', tasks=tasks, remain=len(pages))
        except DbError as e:
            return self.send_db_error(e)


class ChooseCharReviewHandler(BaseHandler):
    URL = '/dzj_char_check.html'

    @authenticated
    def get(self):
        """ 任务大厅-文字校对审定 """
        try:
            pages, tasks = get_my_or_free_tasks(self, 'text_review')
            tasks = [dict(name=p['name'], priority='高',
                          status='待继续' if p.get('text_review_user') else '待领取') for p in tasks]
            self.render('dzj_char_check.html', tasks=tasks, remain=len(pages))
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


class CutProofDetailHandler(BaseHandler):
    URL = '/dzj_(block|column|char)_cut_(proof|review)/([A-Za-z0-9_]+)'

    @authenticated
    def get(self, box_type, stage, name):
        """ 进入切分校对 """
        try:
            task_type = '%s_cut_%s' % (box_type, stage)
            page = convert_bson(self.db.page.find_one(dict(name=name)))
            if not page:
                return self.render('_404.html')
            status_r = page.get(task_type + '_status') != u.STATUS_LOCKED
            user_r = page.get(task_type + '_user') != self.current_user.id
            self.render('dzj_slice_{}detail.html'.format('' if stage == 'proof' else 'check_'),
                        page=page, readonly=status_r or user_r)
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


class CutStatusHandler(BaseHandler):
    URL = '/dzj_mission_slice_status.html'

    @authenticated
    def get(self):
        """ 任务管理-切分状态 """
        def handle_response(body):
            self.render('dzj_mission_slice_status.html', **body)

        self.call_back_api('/api/pages/cut_status', handle_response)
