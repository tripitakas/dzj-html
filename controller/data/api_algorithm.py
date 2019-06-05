#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/3
"""
from controller.base import BaseHandler
import controller.validate as v


class GenerateCharIdApi(BaseHandler):
    URL = '/api/data/gen_char_id'

    def post(self):
        """根据坐标重新生成栏、列、字框的编号"""
        data = self.get_request_data()
        err = v.validate(data, [(v.not_empty, 'blocks', 'columns', 'chars')])
        if err:
            return self.send_error_response(err)
        self.send_data_response(data)
