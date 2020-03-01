#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from bson import json_util
from controller import errors as e
from controller.data.data import Char
from controller.task.task import Task
from controller.base import BaseHandler
from controller.helper import name2code
from controller.task.base import TaskHandler


class CharBrowseHandler(BaseHandler, Char):
    URL = '/data/char/@char_id'

    def get(self, char_id):
        """ 浏览多张字图"""
        char = self.db.char.find_one({'id': char_id})
        if not char:
            return self.send_error_response(e.no_object, message='没有找到字图%s' % char)
        condition = self.get_char_search_condition(self.request.query)[0]
        op = '$lt' if self.get_query_argument('to', '') == 'prev' else '$lt'
        condition['char_code'] = {op: name2code(char_id)}
        docs, pager, q, order = self.find_by_page(condition, default_order='char_code')
