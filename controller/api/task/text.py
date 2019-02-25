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


class GetPageApi(BaseHandler):
    URL = r'/api/page/([A-Za-z0-9_]+)'

    def get(self, name):
        """ 获取页面数据 """
        try:
            if not options.testing and (not self.update_login() or u.ACCESS_DATA_MGR not in self.authority):
                return self.send_error(errors.unauthorized)

            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(convert_bson(page))
        except DbError as e:
            return self.send_db_error(e)


class UnlockTasksApi(BaseHandler):
    URL = r'/api/unlock/(%s)/([A-Z]{2})?' % u.re_task_type

    def get(self, task_type, kind=None):
        """ 退回全部任务 """
        try:
            if not options.testing and (not self.update_login() or u.ACCESS_TASK_MGR not in self.authority):
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TASK_MGR)

            pages = self.db.page.find(dict(kind=kind) if kind else {})
            ret = []
            for page in pages:
                info = {}
                for field in page:
                    if re.match(u.re_task_type, field):
                        info[field] = None
                if info:
                    name = page['name']
                    r = self.db.page.update_one(dict(name=name), {'$set': info})
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_response(ret)
        except DbError as e:
            return self.send_db_error(e)


class PickTaskApi(BaseHandler):
    URL = r'/api/pick/(%s)/([A-Za-z0-9_]+)' % u.re_task_type

    @authenticated
    def get(self, task_type, name):
        """ 取审校任务 """
        try:
            # 检查是否有校对权限
            self.update_login()
            if u.authority_map[task_type] not in self.authority:
                return self.send_error(errors.unauthorized, reason=u.authority_map[task_type])

            # 有未完成的任务则不能继续
            task_user = task_type + '_user'
            names = list(self.db.page.find({task_user: self.current_user.id, task_type + '_status': None}))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error(errors.task_uncompleted, reason=','.join(names))

            # 领取新任务或继续原任务
            lock = {task_user: self.current_user.id, task_type + '_time': datetime.now()}
            r = self.db.page.update_one({task_user: None, 'name': name}, {'$set': lock})
            page = convert_bson(self.db.page.find_one(dict(name=name)))

            if r.matched_count:
                self.add_op_log('pick_' + task_type, file_id=page['id'], context=name)
            else:
                if not page:
                    return self.send_error(errors.no_object)
                if page.get(task_user) != self.current_user.id:
                    return self.send_error(errors.task_locked)
                self.add_op_log('open_' + task_type, file_id=page['id'], context=name)

            # 反馈领取成功
            self.send_response(dict(name=page['name']))
        except DbError as e:
            return self.send_db_error(e)
