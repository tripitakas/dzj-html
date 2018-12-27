#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/12/27
"""

from tornado.web import authenticated
from controller.base import BaseHandler, DbError, convert_bson
from datetime import datetime

import model.user as u
from controller import errors


class PickTextTaskApi(BaseHandler):
    URL = r'/api/pick/text/([A-Za-z0-9_]+)'

    @authenticated
    def get(self, name):
        """ 取文字校对任务 """
        try:
            self.update_login()
            if u.ACCESS_TEXT_PROOF not in self.authority:
                return self.send_error(errors.unauthorized, reason=u.ACCESS_TEXT_PROOF)

            lock = {'text_lock': [self.current_user.id, datetime.now(), 0]}
            r = self.db.cutpage.update_one(dict(text_lock=None, name=name), {'$set': lock})
            page = convert_bson(self.db.cutpage.find_one(dict(name=name)))

            if r.matched_count:
                self.add_op_log(None, 'pick_text_task', file_id=page['id'], context=name)
            else:
                if not page:
                    return self.send_error(errors.no_object)
                lock = page.get('text_lock')
                if not lock or lock[0] != self.current_user.id:
                    return self.send_error(errors.task_locked)

            self.send_response(dict(id=page['id'], name=page['name']))
        except DbError as e:
            return self.send_db_error(e)
