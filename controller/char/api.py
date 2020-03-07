#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
from os import path
from bson.objectid import ObjectId
from controller import errors  as e
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
            script = 'nohup python3 %s/extract_img.py --username="%s" --regen=%s >> log/extract_img.log 2>&1 &'
            os.system(script % (path.dirname(__file__), self.username,
                                int(self.data.get('regen') in ['1', True, 'true'])))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class CharUpdateApi(BaseHandler, Char):
    URL = '/api/char/@oid'

    def post(self, _id):
        """ 更新字符"""

        def check_level():
            return True

        try:
            rules = [(v.not_empty, 'txt'), (v.is_proof_txt, 'txt')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'_id': ObjectId(_id)})
            if not char:
                self.send_error_response(e.no_object, message='没有找到字符')
            if not check_level():
                self.send_error_response(e.data_level_unqualified, message='数据等级不够')

            r = re.findall(r'[XYMN*]', self.data['txt'])
            if r:
                self.data['txt_type'] = r[0]
                self.data['txt'] = self.data['txt'].replace(r[0], '')

            my_log = {k: self.data[k] for k in ['txt', 'txt_type', 'normal_txt', 'remark'] if self.data.get(k)}
            my_log.update({'edit_type': 'char_edit', 'updated_time': self.now()})
            new_log = True
            logs = char.get('txt_logs') or []
            for i, log in enumerate(logs):
                if log['user_id'] == self.user_id:
                    logs[i].update(my_log)
                    new_log = False
            if new_log:
                my_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
                logs.append(my_log)

            update = {k: self.data[k] for k in ['txt', 'txt_type', 'normal_txt'] if self.data.get(k)}
            update['txt_logs'] = logs
            self.db.char.update_one({'_id': ObjectId(_id)}, {'$set': update})
            self.send_data_response(dict(txt_logs=logs))

        except self.DbError as error:
            return self.send_db_error(error)
