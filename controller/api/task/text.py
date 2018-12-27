#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/27
"""

from tornado.web import authenticated
from controller.base import BaseHandler, DbError

import model.user as u
from controller import errors


class PickTextTaskApi(BaseHandler):
    URL = r'/api/pick/text/([A-Za-z0-9_]+)'

    @authenticated
    def get(self, tid):
        """ 取文字校对任务 """
        try:
            self.update_login()
            if u.ACCESS_TEXT_PROOF not in self.authority:
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TEXT_PROOF)

            self.add_op_log(None, 'pick_task', context='todo: task_type_id')
        except DbError as e:
            return self.send_db_error(e)
        self.send_response(dict(id=tid))
