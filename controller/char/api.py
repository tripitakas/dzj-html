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
            script = 'nohup python3 %s/utils/extract_img.py --username=%s --regen=%s >> log/extract_img.log 2>&1 &'
            script = script % (h.BASE_DIR, self.username, int(self.data.get('regen') in ['是', True]))
            # print(script)
            os.system(script)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class CharTxtApi(CharHandler):
    URL = '/api/char/txt/@char_name'

    def post(self, char_name):
        """ 更新字符的txt"""

        try:
            rules = [(v.not_empty, 'txt', 'edit_type'), (v.is_proof_txt, 'txt')]
            self.validate(self.data, rules)
            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到字符')
            # 检查数据等级和积分
            self.check_level_and_point(self, char, 'txt', self.data['edit_type'])
            # 检查参数，设置更新
            r = re.findall(r'[XYMN*]', self.data['txt'])
            if r:
                self.data['txt_type'] = r[0]
                self.data['txt'] = self.data['txt'].replace(r[0], '')
            update = {k: self.data[k] for k in ['txt', 'txt_type', 'ori_txt'] if self.data.get(k)}
            if h.cmp_obj(update, char, ['txt', 'txt_type', 'ori_txt']):
                return self.send_error_response(e.not_changed)

            my_log = {k: self.data[k] for k in ['txt', 'ori_txt', 'remark', 'edit_type'] if self.data.get(k)}
            my_log.update({'txt_type': self.data.get('txt_type'), 'updated_time': self.now()})
            new_log, logs = True, char.get('txt_logs') or []
            for i, log in enumerate(logs):
                if log['user_id'] == self.user_id:
                    logs[i].update(my_log)
                    new_log = False
            if new_log:
                my_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
                logs.append(my_log)
            update.update({'txt_logs': logs, 'txt_level': self.get_user_level(self, 'txt', self.data['edit_type'])})
            # 更新char表
            self.db.char.update_one({'name': char_name}, {'$set': update})
            self.send_data_response(dict(txt_logs=logs))
            self.add_log('update_txt', char['_id'], char['name'], update)

        except self.DbError as error:
            return self.send_db_error(error)


class CharsTxtApi(CharHandler):
    URL = '/api/chars/txt'

    def post(self):
        """ 批量更新txt"""
        try:
            rules = [(v.not_empty, 'names', 'txt', 'edit_type')]
            self.validate(self.data, rules)
            log = dict(un_changed=[], level_unqualified=[], point_unqualified=[])
            chars = list(self.db.char.find({'name': {'$in': self.data['names']}, 'txt': {'$ne': self.data['txt']}}))
            log['un_changed'] = set(self.data['names']) - set(c['name'] for c in chars)
            # 检查数据权限和积分
            qualified = []
            for char in chars:
                r = self.check_level_and_point(self, char, 'txt', self.data['edit_type'], False)
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
            self.db.char.update_many({'name': {'$in': new_update + old_update}}, {'$set': {
                'txt': self.data['txt'], 'txt_level': self.get_user_level(self, 'txt', self.data['edit_type'])
            }})
            if new_update:
                self.db.char.update_many({'name': {'$in': new_update}}, {'$addToSet': {'txt_logs': {
                    'txt': self.data['txt'], 'edit_type': self.data['edit_type'],
                    'user_id': self.user_id, 'username': self.username, 'create_time': self.now()
                }}})
            if old_update:
                cond = {'name': {'$in': old_update}, 'txt_logs.user_id': self.user_id}
                self.db.char.update_many(cond, {'$set': {'txt_logs.$': {
                    'txt': self.data['txt'], 'edit_type': self.data['edit_type'],
                    'updated_time': self.now()
                }}})
            self.send_data_response()
            self.add_log('update_txt', None, new_update + old_update, dict(txt=self.data['txt']))

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

    task2txt = dict(cluster_proof='ocr_txt', cluster_review='ocr_txt', separate_proof='txt',
                    separate_review='txt')

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
        """ 发布聚类、分类的校对、审定任务 """

        def get_task(ps, cnt, remark=None):
            priority = self.data.get('priority') or 2
            pre_tasks = self.data.get('pre_tasks') or [],
            tk = ''.join([p.get('ocr_txt') or p.get('txt') for p in ps])
            return dict(task_type=task_type, num=num, batch=batch, collection='char', id_name='name',
                        txt_kind=tk, char_count=cnt, doc_id=None, steps=None, status=self.STATUS_PUBLISHED,
                        priority=priority, pre_tasks=pre_tasks, params=ps, result={}, remark=remark,
                        create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                        publish_user_id=self.user_id, publish_by=self.username)

        def get_txt(task):
            return ''.join([str(p[field]) for p in task.get('params', [])])

        # 哪个字段
        field = self.task2txt.get(task_type)

        # 统计字频
        counts = list(self.db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]))

        # 去除已发布的任务
        txts = [c['_id'] for c in counts]
        published = list(self.db.task.find({'task_type': task_type, 'num': num, 'params.' + field: {'$in': txts}}))
        if published:
            published = ''.join([get_txt(t) for t in published])
            counts = [c for c in counts if str(c['_id']) not in published]

        # 发布聚类校对-常见字
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            get_task([{field: c['_id'], 'count': c['count'], 'source': source}], c['count'])
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            task_params = [t['params'] for t in normal_tasks]
            self.add_op_log(self.db, 'publish_task', dict(task_type=task_type, task_params=task_params), self.username)

        # 发布聚类校对-生僻字
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        for c in counts2:
            total_count += c['count']
            params.append({field: c['_id'], 'count': c['count'], 'source': source})
            if total_count > 50:
                rare_tasks.append(get_task(params, total_count, '生僻字'))
                params, total_count = [], 0
        if total_count:
            rare_tasks.append(get_task(params, total_count, '生僻字'))
        if rare_tasks:
            self.db.task.insert_many(rare_tasks)
            task_params = [t['params'] for t in normal_tasks]
            self.add_op_log(self.db, 'publish_task', dict(task_type=task_type, task_params=task_params), self.username)

        return dict(published=published, normal_count=len(normal_tasks), rare_count=len(rare_tasks))


class CharTaskClusterApi(CharHandler):
    URL = ['/api/task/do/(cluster_proof|cluster_review)/@task_id',
           '/api/task/update/(cluster_proof|cluster_review)/@task_id']

    def post(self, task_type, task_id):
        """ 提交聚类校对任务"""
        try:
            # 更新char
            params = self.task['params']
            cond = {'source': params[0]['source'], 'ocr_txt': {'$in': [c['ocr_txt'] for c in params]}}
            self.db.char.update_many(cond, {'$inc': {'txt_count.' + task_type: 1}})
            # 提交任务
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
