#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from bson.objectid import ObjectId
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller import helper as h
from controller import validate as v


class CharDeleteApi(CharHandler):
    URL = '/api/(char)/delete'

    def post(self, collection):
        """批量删除"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_log('delete_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_log('delete_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class CharExtractImgApi(CharHandler):
    URL = '/api/char/extract_img'

    def post(self):
        """批量生成字图"""
        try:
            rules = [(v.not_empty, 'type'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = self.get_char_search_condition(self.data['search'])[0]
            count = self.db.char.count_documents(condition)
            self.db.char.update_many(condition, {'$set': {'img_need_updated': True}})
            if count:  # 启动脚本，生成字图
                regen = int(self.data.get('regen') in ['是', True])
                script = 'nohup python3 %s/utils/extract_img.py --username=%s --regen=%s >> log/extract_img_%s.log 2>&1 &'
                script = script % (h.BASE_DIR, self.username, regen, h.get_date_time(fmt='%Y%m%d%H%M%S'))
                print(script)
                os.system(script)
                self.send_data_response(count=count)
            else:
                self.send_error_response(e.no_object, message='找不到对应的字数据')

        except self.DbError as error:
            return self.send_db_error(error)


class CharTxtApi(CharHandler):
    URL = '/api/char/txt/@char_name'

    def post(self, char_name):
        """更新字符的txt"""

        try:
            rules = [(v.not_none, 'txt', 'txt_type'), (v.is_txt_type, 'txt_type')]
            self.validate(self.data, rules)

            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到字符')
            # 检查数据等级和积分
            self.check_txt_level_and_point(self, char, self.data.get('task_type'))
            # 检查参数，设置更新
            fields = ['txt', 'nor_txt', 'txt_type', 'remark']
            update = {k: self.data[k] for k in fields if self.data.get(k) not in ['', None]}
            if h.cmp_obj(update, char, fields):
                return self.send_error_response(e.not_changed)
            my_log = {k: self.data[k] for k in fields + ['task_type'] if self.data.get(k) not in ['', None]}
            my_log.update({'updated_time': self.now()})
            new_log, logs = True, char.get('txt_logs') or []
            for i, log in enumerate(logs):
                if log.get('user_id') == self.user_id:
                    logs[i].update(my_log)
                    new_log = False
            if new_log:
                my_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
                logs.append(my_log)
            # 更新char表
            update.update({'txt_logs': logs, 'txt_level': self.get_user_txt_level(self, self.data.get('task_type'))})
            self.db.char.update_one({'name': char_name}, {'$set': update})
            self.send_data_response(dict(txt_logs=logs))
            self.add_log('update_txt', char['_id'], char['name'], update)

        except self.DbError as error:
            return self.send_db_error(error)


class CharsTxtApi(CharHandler):
    URL = '/api/chars/(txt|txt_type)'

    def post(self, field):
        """批量更新txt"""
        try:
            rules = [(v.not_empty, 'names', field)]
            self.validate(self.data, rules)

            task_type = self.data.get('task_type')
            log = dict(un_changed=[], level_unqualified=[], point_unqualified=[])
            chars = list(self.db.char.find({'name': {'$in': self.data['names']}, field: {'$ne': self.data[field]}}))
            log['un_changed'] = set(self.data['names']) - set(c['name'] for c in chars)
            # 检查数据权限和积分
            qualified = []
            for char in chars:
                r = self.check_txt_level_and_point(self, char, task_type, False)
                if isinstance(r, tuple):
                    if r[0] == e.data_level_unqualified[0]:
                        log['level_unqualified'].append(char['name'])
                    elif r[0] == e.data_point_unqualified[0]:
                        log['point_unqualified'].append(char['name'])
                else:
                    qualified.append(char)

            # 检查用户是否修改过字符
            new_update, old_update = [], []
            for char in qualified:
                if char.get('txt_logs') and [log for log in char['txt_logs'] if log.get('user_id') == self.user_id]:
                    old_update.append(char['name'])
                else:
                    new_update.append(char['name'])

            # 更新char表的txt/txt_level/txt_logs字段
            info = {field: self.data[field], 'txt_level': self.get_user_txt_level(self, task_type)}
            self.db.char.update_many({'name': {'$in': new_update + old_update}}, {'$set': info})
            log['updated'] = new_update + old_update
            if new_update:
                self.db.char.update_many({'name': {'$in': new_update}, 'txt_logs': None}, {'$set': {'txt_logs': []}})
                self.db.char.update_many({'name': {'$in': new_update}}, {'$addToSet': {'txt_logs': {
                    **info, 'user_id': self.user_id, 'username': self.username,
                    'create_time': self.now(), 'updated_time': self.now()
                }}})
            if old_update:
                cond = {'name': {'$in': old_update}, 'txt_logs.user_id': self.user_id}
                self.db.char.update_many(cond, {'$set': {
                    'txt_logs.$.' + field: info[field],
                    'txt_logs.$.txt_level': info['txt_level'],
                    'txt_logs.$.updated_time': self.now(),
                }})
            self.send_data_response({k: l for k, l in log.items() if l})
            self.add_log('update_txt', None, new_update + old_update, info)

        except self.DbError as error:
            return self.send_db_error(error)


class CharSourceApi(CharHandler):
    URL = '/api/char/source'

    def post(self):
        """批量更新批次"""
        try:
            rules = [(v.not_empty, 'type', 'source'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = Char.get_char_search_condition(self.data['search'])[0]
            r = self.db.char.update_many(condition, {'$set': {'source': self.data['source']}})
            self.send_data_response(dict(matched_count=r.matched_count))
            self.add_log('update_char', self.data['_ids'], None, dict(source=self.data['source']))

        except self.DbError as error:
            return self.send_db_error(error)
