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
from .base import CharHandler
from .publish import PublishHandler


class PublishCharTasksApi(PublishHandler):
    URL = r'/api/char/publish_task'

    def post(self):
        """ 发布字任务 """
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)

            if not self.db.char.count_documents({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])

            try:
                log = self.publish_many(self.data['batch'], self.data['task_type'], self.data['source'],
                                        self.data.get('num'))
                return self.send_data_response(log)

            except self.DbError as error:
                return self.send_db_error(error)

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
            script = 'nohup python3 %s/extract_img.py --username="%s" --regen=%s >> log/extract_img.log 2>&1 &'
            print(script % (path.dirname(__file__), self.username, int(self.data.get('regen') in ['是', True])))
            os.system(script % (path.dirname(__file__), self.username, int(self.data.get('regen') in ['是', True])))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class UpdateCharSourceApi(BaseHandler, Char):
    URL = '/api/data/char/source'

    def post(self):
        """ 批量更新批次"""
        try:
            rules = [(v.not_empty, 'type', 'source'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)
            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = self.get_char_search_condition(self.data['search'])[0]
            r = self.db.char.update_many(condition, {'$set': {'source': self.data['source']}})
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class CharUpdateApi(CharHandler):
    URL = '/api/char/@oid'

    def post(self, _id):
        """ 更新字符"""

        def check_level():
            # 暂时简单考虑data_level和updated_count两个参数
            has_data_level = self.get_user_level() >= (char.get('data_level') or 0)
            updated_count = len(char.get('txt_logs') or [])
            is_count_qualified = self.get_updated_char_count() >= updated_count * 100
            return has_data_level and is_count_qualified

        try:
            rules = [(v.not_empty, 'txt', 'edit_type'), (v.is_proof_txt, 'txt')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'_id': ObjectId(_id)})
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
            update = {'txt_logs': logs, 'data_level': self.get_edit_level(self.data['edit_type'])}
            update.update({k: self.data[k] for k in ['txt', 'txt_type', 'ori_txt'] if self.data.get(k)})
            self.db.char.update_one({'_id': ObjectId(_id)}, {'$set': update})
            self.send_data_response(dict(txt_logs=logs))

        except self.DbError as error:
            return self.send_db_error(error)


class TaskCharClusterProofApi(CharHandler):
    URL = ['/api/task/do/cluster_proof/@task_id',
           '/api/task/update/cluster_proof/@task_id']

    def post(self, task_id):
        """ 提交聚类校对任务"""
        try:
            # 更新char
            params = self.task['params']
            cond = {'source': params[0]['source'], 'ocr_txt': {'$in': [c['ocr_txt'] for c in params]}}
            self.db.char.update_many(cond, {'$inc': {'proof_count': 1}})
            # 提交任务
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
