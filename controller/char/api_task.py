#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller import helper as h
from controller import validate as v


class CharTaskPublishApi(CharHandler):
    URL = r'/api/char/task/publish'

    def post(self):
        """ 发布字任务"""
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)
            if not self.db.char.count_documents({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])
            log = self.publish_char_task()
            return self.send_data_response(log)

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def get_txt(task, field):
        """ 获取任务相关的文字"""
        return ''.join([str(p[field]) for p in task.get('params', [])])

    def task_meta(self, task_type, params, cnt, field):
        batch = self.data['batch']
        num = int(self.data.get('num') or 1)
        priority = int(self.data.get('priority') or 2)
        pre_tasks = self.data.get('pre_tasks') or []
        is_oriented = self.data.get('is_oriented') == '1'
        txt_kind = ''.join([p[field] for p in params if p.get(field)])
        task = dict(task_type=task_type, num=num, batch=batch, status=self.STATUS_PUBLISHED, priority=priority,
                    steps={}, pre_tasks=pre_tasks, is_oriented=is_oriented, collection='char', id_name='name',
                    doc_id=None, char_count=cnt, txt_kind=txt_kind, required_count=None, params=params or {}, result={},
                    create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                    publish_user_id=self.user_id, publish_by=self.username)
        not is_oriented and task.pop('is_oriented', 0)
        return task

    def publish_char_task(self):
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
        cond = {'task_type': task_type, 'num': num, 'params.source': source}
        published = list(self.db.task.find(cond))
        if published:
            published = ''.join([self.get_txt(t, field) for t in published])
            counts = [c for c in counts if str(c['_id']) not in published]

        # 针对常见字(字频大于等于50)，发布聚类校对
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            self.task_meta(task_type, [{field: c['_id'], 'count': c['count'], 'source': source}], c['count'], field)
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            log.append(dict(task_type=task_type, task_params=[t['params'] for t in normal_tasks]))

        # 针对生僻字(字频小于50)，发布生僻校对。发布任务时，字种不超过10个。
        rare_type = task_type  # 生僻校对的任务类型同聚类校对
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        for c in counts2:
            total_count += c['count']
            params.append({field: c['_id'], 'count': c['count'], 'source': source})
            if total_count >= 50 or len(params) >= 10:
                rare_tasks.append(self.task_meta(rare_type, params, total_count, field))
                params, total_count = [], 0
        if total_count:
            rare_tasks.append(self.task_meta(rare_type, params, total_count, field))
        if rare_tasks:
            self.db.task.insert_many(rare_tasks)
            log.append(dict(task_type=rare_type, task_params=[t['params'] for t in rare_tasks]))

        self.add_op_log(self.db, 'publish_task', None, log, self.username)
        # 启动脚本，更新required_count
        script = 'nohup python3 %s/utils/update_char.py --func=update_task_required_count --batch=%s --renew=1 >> log/update_char_%s.log 2>&1 &'
        script = script % (h.BASE_DIR, self.data['batch'], h.get_date_time(fmt='%Y%m%d%H%M%S'))
        print(script)
        os.system(script)

        return dict(published=published, normal_count=len(normal_tasks), rare_count=len(rare_tasks))


class CharTaskClusterApi(CharHandler):
    URL = ['/api/task/do/@char_task/@task_id',
           '/api/task/update/@char_task/@task_id']

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
            cond.update({'un_required': None, 'source': params[0]['source'],
                         'ocr_txt': {'$in': [c['ocr_txt'] for c in params]}})
            if self.db.char.count_documents(cond):
                return self.send_error_response(e.task_submit_error, message='还有未提交的字图，不能提交任务')
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
