#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
from os import path
from bson.objectid import ObjectId
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller import validate as v


class CharGenImgApi(CharHandler):
    URL = '/api/char/gen_img'

    def post(self):
        """ 批量生成字图"""
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
            print(script % (path.dirname(__file__), self.username, int(self.data.get('regen') in ['是', True])))
            os.system(script % (path.dirname(__file__), self.username, int(self.data.get('regen') in ['是', True])))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class CharUpdateApi(CharHandler):
    URL = '/api/char/@char_name'

    def post(self, char_name):
        """ 更新字符的txt"""

        def check_level():
            # 暂时简单考虑data_level和updated_count两个参数
            has_data_level = self.get_user_level('txt') >= (char.get('data_level') or 0)
            updated_count = len(char.get('txt_logs') or [])
            is_count_qualified = self.get_updated_char_count() >= updated_count * 100
            return has_data_level and is_count_qualified

        try:
            rules = [(v.not_empty, 'txt', 'edit_type'), (v.is_proof_txt, 'txt')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'name': char_name})
            if not char:
                self.send_error_response(e.no_object, message='没有找到字符')
            if not check_level() and char.get('txt_logs')[-1]['user_id'] != self.user_id:
                self.send_error_response(e.data_level_unqualified, message='数据等级不够')

            r = re.findall(r'[XYMN*]', self.data['txt'])
            if r:
                self.data['txt_type'] = r[0]
                self.data['txt'] = self.data['txt'].replace(r[0], '')

            my_log = {k: self.data[k] for k in ['txt', 'ori_txt', 'remark', 'edit_type'] if self.data.get(k)}
            my_log.update({'txt_type': self.data.get('txt_type'), 'updated_time': self.now()})
            new_log = True
            logs = char.get('txt_logs') or []
            for i, log in enumerate(logs):
                if log['user_id'] == self.user_id:
                    logs[i].update(my_log)
                    new_log = False
            if new_log:
                my_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
                logs.append(my_log)
            update = {'txt_logs': logs, 'data_level': self.get_edit_level('txt', self.data['edit_type'])}
            update.update({k: self.data[k] for k in ['txt', 'txt_type', 'ori_txt'] if self.data.get(k)})
            self.db.char.update_one({'name': char_name}, {'$set': update})
            self.send_data_response(dict(txt_logs=logs))

        except self.DbError as error:
            return self.send_db_error(error)


class CharSourceApi(CharHandler):
    URL = '/api/char/source'

    def post(self):
        """ 批量更新批次"""
        try:
            rules = [(v.not_empty, 'type', 'source'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)
            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = Char.get_char_search_condition(self.data['search'])[0]
            r = self.db.char.update_many(condition, {'$set': {'source': self.data['source']}})
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)
