#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from bson import json_util
from controller.base import BaseHandler, DbError


class SessionConfigApi(BaseHandler):
    URL = '/api/session/config'

    def post(self):
        """ 配置后台cookie"""
        try:
            data = self.get_request_data()
            for k, v in data.items():
                self.set_secure_cookie(k, json_util.dumps(v))
            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)
