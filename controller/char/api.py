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
            rules = [(v.not_none, 'txt', 'txt_type', 'is_variant'),
                     (v.is_txt, 'txt'), (v.is_txt_type, 'txt_type')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到字符')
            # 检查数据等级和积分
            self.check_txt_level_and_point(self, char, self.data.get('task_type'))
            # 检查参数，设置更新
            fields = ['txt', 'ori_txt', 'txt_type', 'is_variant']
            update = {k: self.data[k] for k in fields if self.data.get(k) not in ['', None]}
            if h.cmp_obj(update, char, fields):
                return self.send_error_response(e.not_changed)
            my_log = {k: self.data[k] for k in fields + ['remark', 'task_type'] if self.data.get(k) not in ['', None]}
            my_log.update({'updated_time': self.now()})
            new_log, logs = True, char.get('txt_logs') or []
            for i, log in enumerate(logs):
                if log['user_id'] == self.user_id:
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
    URL = '/api/chars/(txt|ori_txt)'

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
                self.db.char.update_many(cond, {'$set': {'txt_logs.$': {
                    **info, 'updated_time': self.now()
                }}})
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

    task2txt = dict(cluster_proof='ocr_txt', cluster_review='ocr_txt', rare_proof='ocr_txt',
                    rare_review='ocr_txt', variant_proof='txt', variant_review='txt')

    def post(self):
        """ 发布字任务"""
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)
            if not self.db.char.count_documents({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])

            log = self.check_and_publish(self.data['batch'], self.data['source'], self.data['task_type'],
                                         self.data.get('num'))
            return self.send_data_response(log)

        except self.DbError as error:
            return self.send_db_error(error)

    def check_and_publish(self, batch='', source='', task_type='', num=None):
        """ 发布聚类校对、审定任务 """

        def get_task(tsk_type, ps, cnt):
            priority = self.data.get('priority') or 2
            pre_tasks = self.data.get('pre_tasks') or []
            tk = ''.join([p.get('ocr_txt') or p.get('txt') for p in ps])
            return dict(task_type=tsk_type, num=num, batch=batch, collection='char', id_name='name',
                        txt_kind=tk, char_count=cnt, doc_id=None, steps=None, status=self.STATUS_PUBLISHED,
                        priority=priority, pre_tasks=pre_tasks, params=ps, result={},
                        create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                        publish_user_id=self.user_id, publish_by=self.username)

        def get_txt(task):
            return ''.join([str(p[field]) for p in task.get('params', [])])

        # 以哪个字段进行聚类
        field = self.task2txt.get(task_type)
        log = []

        # 统计字频
        counts = list(self.db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]))

        # 去除已发布的任务
        rare_type = task_type.replace('cluster', 'rare')
        published = list(
            self.db.task.find({'task_type': {'$in': [task_type, rare_type]}, 'num': num, 'params.source': source}))
        if published:
            published = ''.join([get_txt(t) for t in published])
            counts = [c for c in counts if str(c['_id']) not in published]

        # 针对常见字，发布聚类校对
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            get_task(task_type, [{field: c['_id'], 'count': c['count'], 'source': source}], c['count'])
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            log.append(dict(task_type=task_type, task_params=[t['params'] for t in normal_tasks]))

        # 针对生僻字，发布生僻校对
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        for c in counts2:
            total_count += c['count']
            params.append({field: c['_id'], 'count': c['count'], 'source': source})
            if total_count > 50:
                rare_tasks.append(get_task(rare_type, params, total_count))
                params, total_count = [], 0
        if total_count:
            rare_tasks.append(get_task(task_type.replace('cluster', 'rare'), params, total_count))
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
            char_ids = self.data.get('char_ids')
            if char_ids:  # 提交当前页
                cond.update({'_id': {'$in': [ObjectId(_id) for _id in char_ids]}})
                self.db.char.update_many(cond, {'$addToSet': {'tasks.' + task_type: self.task['_id']}})
                return self.send_data_response()
            # 提交任务
            params = self.task['params']
            cond.update({'source': params[0]['source'], 'ocr_txt': {'$in': [c['ocr_txt'] for c in params]}})
            chars = self.db.char.find(cond)
            print([c['name'] for c in chars])
            if self.db.char.count_documents(cond):
                return self.send_error_response(e.task_submit_error, message='还有未提交的字图，不能提交任务')
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
