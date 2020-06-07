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
        """ 批量删除 """
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
            script = 'nohup python3 %s/utils/extract_img.py --username=%s --regen=%s >> log/extract_img.log 2>&1 &'
            script = script % (h.BASE_DIR, self.username, int(self.data.get('regen') in ['是', True]))
            print(script)
            os.system(script)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class CharTxtApi(CharHandler):
    URL = '/api/char/txt/@char_name'

    def post(self, char_name):
        """ 更新字符的txt"""

        try:
            rules = [(v.not_none, 'txt', 'txt_type'), (v.is_txt, 'txt'), (v.is_txt_type, 'txt_type')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到字符')
            # 检查数据等级和积分
            self.check_txt_level_and_point(self, char, self.data.get('task_type'))
            # 检查参数，设置更新
            fields = ['txt', 'nor_txt', 'txt_type']
            update = {k: self.data[k] for k in fields if self.data.get(k) not in ['', None]}
            if h.cmp_obj(update, char, fields):
                return self.send_error_response(e.not_changed)
            my_log = {k: self.data[k] for k in fields + ['remark', 'task_type'] if self.data.get(k) not in ['', None]}
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
        """ 批量更新txt"""
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
            self.add_log('update_char', self.data['_ids'], None, dict(source=self.data['source']))

        except self.DbError as error:
            return self.send_db_error(error)


class CharTaskPublishApi(CharHandler):
    URL = r'/api/char/task/publish'

    def post(self):
        """ 发布字任务"""
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)
            if not self.db.char.count_documents({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])
            log = self.publish_cluster_task()
            return self.send_data_response(log)

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def get_txt(task, field):
        """ 获取任务相关的文字"""
        return ''.join([str(p[field]) for p in task.get('params', [])])

    def task_meta(self, task_type, params, cnt):
        batch = self.data['batch']
        num = int(self.data.get('num') or 1)
        priority = self.data.get('priority') or 2
        pre_tasks = self.data.get('pre_tasks') or []
        txt_kind = ''.join([p.get('ocr_txt') or '' for p in params])
        return dict(task_type=task_type, num=num, batch=batch, collection='char', id_name='name',
                    txt_kind=txt_kind, char_count=cnt, doc_id=None, steps=None, status=self.STATUS_PUBLISHED,
                    priority=priority, pre_tasks=pre_tasks, params=params, result={},
                    create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                    publish_user_id=self.user_id, publish_by=self.username)

    def publish_cluster_task(self):
        """ 发布聚类校对、审定任务 """

        log = []
        source = self.data['source']
        task_type = self.data['task_type']
        num = int(self.data.get('num') or 1)  # 默认校次为1

        # 统计字频
        field = 'ocr_txt'  # 以哪个字段进行聚类
        counts = list(self.db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))

        # 去除已发布的任务
        rare_type = task_type.replace('cluster', 'rare')
        cond = {'task_type': {'$in': [task_type, rare_type]}, 'num': num, 'params.source': source}
        published = list(self.db.task.find(cond))
        if published:
            published = ''.join([self.get_txt(t, field) for t in published])
            counts = [c for c in counts if str(c['_id']) not in published]

        # 针对常见字(字频大于等于50)，发布聚类校对
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            self.task_meta(task_type, [{field: c['_id'], 'count': c['count'], 'source': source}], c['count'])
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            log.append(dict(task_type=task_type, task_params=[t['params'] for t in normal_tasks]))

        # 针对生僻字(字频小于50)，发布生僻校对。发布任务时，字种不超过10个。
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        for c in counts2:
            total_count += c['count']
            params.append({field: c['_id'], 'count': c['count'], 'source': source})
            if total_count >= 50 or len(params) >= 10:
                rare_tasks.append(self.task_meta(rare_type, params, total_count))
                params, total_count = [], 0
        if total_count:
            rare_tasks.append(self.task_meta(rare_type, params, total_count))
        if rare_tasks:
            self.db.task.insert_many(rare_tasks)
            log.append(dict(task_type=rare_type, task_params=[t['params'] for t in rare_tasks]))

        self.add_op_log(self.db, 'publish_task', None, log, self.username)
        return dict(published=published, normal_count=len(normal_tasks), rare_count=len(rare_tasks))


class CharTaskClusterApi(CharHandler):
    URL = ['/api/task/do/@cluster_task/@task_id',
           '/api/task/update/@cluster_task/@task_id']

    def post(self, task_type, task_id):
        """ 提交聚类校对任务"""
        try:
            user_level = self.get_user_txt_level(self, task_type)
            cond = {'tasks.' + task_type: {'$ne': self.task['_id']}, 'txt_level': {'$lte': user_level}}
            char_names = self.data.get('char_names')
            if char_names:  # 提交当前页
                cond.update({'name': {'$in': char_names}})
                self.db.char.update_many(cond, {'$addToSet': {'tasks.' + task_type: self.task['_id']}})
                return self.send_data_response()
            # 提交任务
            params = self.task['params']
            cond.update({'source': params[0]['source'], 'ocr_txt': {'$in': [c['ocr_txt'] for c in params]}})
            if self.db.char.count_documents(cond):
                return self.send_error_response(e.task_submit_error, message='还有未提交的字图，不能提交任务')
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
