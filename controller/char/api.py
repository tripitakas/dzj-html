#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os import path
from bson.objectid import ObjectId
from controller import validate as v
from controller.data.data import Char
from controller.base import BaseHandler


class CharGenImgApi(BaseHandler, Char):
    URL = '/api/char/gen_img'

    def post(self):
        """ 批量生成字图 """
        try:
            rules = [(v.not_empty, 'type'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = self.get_char_search_condition(self.data['search'])[0]

            self.db.char.update_many(condition, {'$set': {'img_need_updated': True}})

            # 启动脚本，生成字图
            script = ['nohup', 'python3', path.join(self.application.BASE_DIR, 'utils', 'extract_cut_img.py')]
            os.system(' '.join(script) + ' >> log/cut_img.log 2>&1 &')

            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class GetColumnUrlApi(BaseHandler, Char):
    URL = '/api/char/column_url'

    def post(self):
        """ 获取列图路径"""
        try:
            rules = [(v.not_empty, 'column_id')]
            self.validate(self.data, rules)

            url = self.get_web_img(self.data['column_id'], img_type='column')
            self.send_data_response(dict(url=url))

        except self.DbError as error:
            return self.send_db_error(error)
