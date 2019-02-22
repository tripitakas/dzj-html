#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/27
"""

from tornado.web import authenticated
from tornado.options import options
from controller.base import BaseHandler, DbError, convert_bson
from datetime import datetime

import model.user as u
from controller import errors


class GetTextApi(BaseHandler):
    URL = r'/api/get/text/([A-Za-z0-9_]+)'

    def get(self, name):
        """ 获取页面数据 """
        try:
            if not options.testing and (not self.update_login() or u.ACCESS_TEXT_PROOF not in self.authority):
                return self.send_error(errors.unauthorized)

            page = self.db.cutpage.find_one(dict(name=name))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(convert_bson(page))
        except DbError as e:
            return self.send_db_error(e)


class PickTextTaskApi(BaseHandler):
    URL = r'/api/pick/text/([A-Za-z0-9_]+)'

    @authenticated
    def get(self, name):
        """ 取文字校对任务 """
        try:
            # 检查是否有校对权限
            self.update_login()
            if u.ACCESS_TEXT_PROOF not in self.authority:
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TEXT_PROOF)

            # 有未完成的任务则不能继续
            names = list(self.db.cutpage.find(dict(text_lock_user=self.current_user.id, text_status=None)))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error(errors.task_uncompleted, reason=','.join(names))

            # 领取新任务或继续原任务
            lock = dict(text_lock_user=self.current_user.id, text_lock_time=datetime.now())
            r = self.db.cutpage.update_one(dict(text_lock_user=None, name=name), {'$set': lock})
            page = convert_bson(self.db.cutpage.find_one(dict(name=name)))

            if r.matched_count:
                self.add_op_log('pick_text_task', file_id=page['id'], context=name)
            else:
                if not page:
                    return self.send_error(errors.no_object)
                if page.get('text_lock_user') != self.current_user.id:
                    return self.send_error(errors.task_locked)

            # 反馈领取成功
            self.send_response(dict(name=page['name']))
        except DbError as e:
            return self.send_db_error(e)
