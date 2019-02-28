#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""

from tornado.web import authenticated
from tornado.options import options
from controller.base import BaseHandler, DbError, convert_bson
from datetime import datetime

import model.user as u
from controller import errors
import re
from functools import cmp_to_key


class GetPageApi(BaseHandler):
    URL = r'/api/page/([A-Za-z0-9_]+)'

    def get(self, name):
        """ 获取页面数据 """
        try:
            if not options.testing and (not self.update_login() or not self.authority):
                return self.send_error(errors.unauthorized)

            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(convert_bson(page))
        except DbError as e:
            self.send_db_error(e)


class GetPagesApi(BaseHandler):
    URL = r'/api/pages/([a-z_]+)'

    def get(self, kind):
        """ 为任务管理获取页面列表 """
        self.process(kind)

    def post(self, kind):
        """ 为任务管理获取页面列表 """
        self.process(kind)

    def process(self, kind):
        try:
            if not options.testing and (not self.update_login() or (
                            u.ACCESS_DATA_MGR not in self.authority and u.ACCESS_TASK_MGR not in self.authority)):
                return self.send_error(errors.unauthorized)

            assert 'cut_' in kind or 'text_' in kind
            if 'cut_' in kind:
                all_types = ['block_cut_proof', 'column_cut_proof', 'char_cut_proof',
                             'block_cut_review', 'column_cut_review', 'char_cut_review']
            else:
                all_types = ['text1_proof', 'text2_proof', 'text3_proof', 'text_review']

            if kind == 'cut_start' or kind == 'text_start':
                data = self.get_body_obj(StartTask)
                task_types = [t for t in (data.types or '').split(',') if t in all_types]
                task_types = task_types or all_types

                pages = self.db.page.find({'$or': [{t + '_status': None} for t in task_types]})
                self.send_response([p['name'] for p in pages])
            else:
                pages = [convert_bson(p) for p in self.db.page.find({})
                         if [t for t in all_types if p.get(t + '_status')]]
                for p in pages:
                    for field, value in list(p.items()):
                        if field == 'txt':
                            p[field] = len(p[field])
                        elif isinstance(value, list):
                            del p[field]
                self.send_response(pages)
        except DbError as e:
            self.send_db_error(e)


class UnlockTasksApi(BaseHandler):
    URL = r'/api/unlock/(%s)/([A-Za-z0-9_]*)', u.re_task_type + '|cut_proof|cut_review'

    def get(self, task_type, prefix=None):
        """ 退回全部任务 """
        try:
            if not options.testing and (not self.update_login() or u.ACCESS_TASK_MGR not in self.authority):
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TASK_MGR)

            pages = self.db.page.find(dict(name=re.compile('^' + prefix)) if prefix else {})
            ret = []
            for page in pages:
                info = {}
                for field in page:
                    if re.match(u.re_task_type, field) and task_type in field:
                        info[field] = None
                if info:
                    name = page['name']
                    r = self.db.page.update_one(dict(name=name), {'$unset': info})
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_response(ret)
        except DbError as e:
            self.send_db_error(e)


class StartTask(object):
    types = str
    pages = str


class StartTasksApi(BaseHandler):
    URL = r'/api/start/([A-Za-z0-9_]*)'

    @authenticated
    def post(self, prefix=''):
        """ 发布审校任务 """
        try:
            data = self.get_body_obj(StartTask)
            task_types = sorted(list(set([t for t in data.types.split(',') if t in u.task_types])),
                                key=cmp_to_key(lambda a, b: u.task_types.index(a) - u.task_types.index(b)))
            data.pages = data.pages and data.pages.split(',')

            # 检查任务管理权限
            if not self.update_login() or u.ACCESS_TASK_MGR not in self.authority:
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TASK_MGR)

            # 得到待发布的页面
            pages = self.db.page.find(dict(name=re.compile('^' + prefix)) if prefix else {})
            names, items = set(), []
            for page in pages:
                name = page['name']
                if data.pages and name not in data.pages:
                    continue
                for i, task_type in enumerate(task_types):
                    task_status = task_type + '_status'
                    # 不重复发布任务
                    if page.get(task_status):
                        continue
                    # 是第一轮任务就为待领取，否则要等前一轮完成才能继续
                    status = u.STATUS_PENDING if i or self.has_pre_task(page, task_type) else u.STATUS_OPENED
                    r = self.db.page.update_one(dict(name=name), {'$set': {task_status: status}})
                    if r.modified_count:
                        self.add_op_log('start_' + task_type, file_id=str(page['_id']), context=name)
                        names.add(name)
                        items.append(dict(name=name, task_type=task_type, status=status))

            self.send_response(dict(names=list(names), items=items, task_types=task_types))
        except DbError as e:
            self.send_db_error(e)

    @staticmethod
    def has_pre_task(page, task_type):
        idx = u.task_types.index(task_type)
        for i in range(idx):
            status = page.get(u.task_types[i] + '_status')
            if status and status != u.STATUS_ENDED:
                return True


class PickTaskApi(BaseHandler):
    URL = r'/api/pick/(%s)/([A-Za-z0-9_]+)', u.re_task_type

    @authenticated
    def get(self, task_type, name):
        """ 取审校任务 """
        try:
            # 检查是否有校对权限
            self.update_login()
            authority = u.authority_map[u.task_type_authority.get(task_type, task_type)]
            if authority not in self.authority:
                return self.send_error(errors.unauthorized, reason=authority)

            # 有未完成的任务则不能继续
            task_user = task_type + '_user'
            task_status = task_type + '_status'
            names = list(self.db.page.find({task_user: self.current_user.id, task_status: u.STATUS_LOCKED}))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error(errors.task_uncompleted, reason=','.join(names))

            # 领取新任务(待领取或已退回时)或继续原任务
            can_lock = {
                task_user: None,
                'name': name,
                '$or': [{task_status: u.STATUS_OPENED}, {task_status: u.STATUS_RETURNED}]
            }
            lock = {
                task_user: self.current_user.id,
                task_type + '_nickname': self.current_user.name,
                task_status: u.STATUS_LOCKED,
                task_type + '_start_time': datetime.now()
            }
            r = self.db.page.update_one(can_lock, {'$set': lock})
            page = convert_bson(self.db.page.find_one(dict(name=name)))

            if r.matched_count:
                self.add_op_log('pick_' + task_type, file_id=page['id'], context=name)
            elif page and page.get(task_user) == self.current_user.id and page.get(task_status) == u.STATUS_LOCKED:
                self.add_op_log('open_' + task_type, file_id=page['id'], context=name)
            else:
                return self.send_error(errors.task_locked if page else errors.no_object)

            # 反馈领取成功
            assert page.get(task_status) == u.STATUS_LOCKED
            self.send_response(dict(name=page['name']))
        except DbError as e:
            self.send_db_error(e)
