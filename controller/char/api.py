#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import csv
from os import path
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from utils.build_js import build_js
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler
from controller.data.data import Tripitaka, Reel, Sutra, Volume


class CharUpdateSourceApi(BaseHandler):
    URL = '/api/char/source'

    def post(self):
        """ 批量更新分类 """
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.char.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_op_log('update_char', target_id=self.data['_id'])
            else:
                r = self.db.char.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_op_log('update_char', target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


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
            script = ['python3', path.join(self.application.BASE_DIR, 'utils', 'extract_cut_img.py')]
            os.system(' '.join(script))

            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
