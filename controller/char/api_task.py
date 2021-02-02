#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller import helper as h
from controller import validate as v
from utils.update_task import update_txt_equals


class CharTaskPublishApi(CharHandler):
    URL = r'/api/char/task/publish'

    def post(self):
        """发布字任务"""
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)
            if not self.db.char.find_one({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])

            cond, ret = self.publish_char_task()
            self.send_data_response(ret)

            update_txt_equals(self.db, cond=cond)  # 更新txt_equals

        except self.DbError as error:
            return self.send_db_error(error)

    def task_meta(self, task_type, base_txts, source, cnt):
        batch = self.data['batch']
        num = int(self.data.get('num') or 1)
        pre_tasks = self.data.get('pre_tasks') or []
        priority = int(self.data.get('priority') or 2)
        is_oriented = self.data.get('is_oriented') == '1'
        task = dict(task_type=task_type, num=num, batch=batch, status=self.STATUS_PUBLISHED, priority=priority,
                    steps={}, pre_tasks=pre_tasks, is_oriented=is_oriented, collection='char', id_name='name',
                    doc_id='', base_txts=base_txts, char_count=cnt, params=dict(source=source), txt_equals={},
                    result={}, create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                    publish_user_id=self.user_id, publish_by=self.username)
        not is_oriented and task.pop('is_oriented', 0)
        return task

    def publish_char_task(self):
        """发布聚类校对、审定任务"""
        log = []
        source = self.data['source']
        task_type = self.data['task_type']
        num = int(self.data.get('num') or 1)
        # 检查是否已发布
        cond = {'task_type': task_type, 'num': num, 'params.source': source}
        if self.db.task.find_one(cond):
            msg = '数据分类%s已发布过%s#%s的任务' % (source, self.get_task_name(task_type), num)
            self.send_error_response(e.task_failed, message=msg)
        # 根据数据分类，统计字频
        b_field = self.get_base_field(task_type)  # cmb_txt/rvw_txt
        counts = list(self.db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + b_field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        # 针对常见字(字频大于等于50)，发布聚类校对
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            self.task_meta(task_type, [{'txt': c['_id'], 'count': c['count']}], source, c['count'])
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            log.append(dict(task_type=task_type, base_txts=[t['base_txts'] for t in normal_tasks]))
        # 针对生僻字(字频小于50)，发布生僻校对（发布任务时，字种不超过10个）
        rare_type = task_type  # 生僻校对的任务类型同聚类校对
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks, base_txts, total_count = [], [], 0
        for c in counts2:
            total_count += c['count']
            base_txts.append({'txt': c['_id'], 'count': c['count']})
            if total_count >= 50 or len(base_txts) >= 10:
                rare_tasks.append(self.task_meta(rare_type, base_txts, source, total_count))
                base_txts, total_count = [], 0  # reset
        if total_count:
            rare_tasks.append(self.task_meta(rare_type, base_txts, source, total_count))
        if rare_tasks:
            self.db.task.insert_many(rare_tasks)
            log.append(dict(task_type=rare_type, base_txts=[t['base_txts'] for t in rare_tasks]))
        self.add_op_log(self.db, 'publish_task', None, log, self.username)
        return cond, dict(normal_count=len(normal_tasks), rare_count=len(rare_tasks))


class CharTaskClusterApi(CharHandler):
    URL = ['/api/task/do/@char_task/@task_id',
           '/api/task/update/@char_task/@task_id']

    def post(self, task_type, task_id):
        """提交聚类校对任务"""
        try:
            user_level = self.get_user_txt_level(self, task_type)
            cond = {'tasks.' + task_type: {'$ne': self.task['_id']}, 'txt_level': {'$lte': user_level}}
            if self.data.get('char_names'):  # 提交单页
                cond.update({'name': {'$in': self.data.get('char_names')}})
                self.db.char.update_many(cond, {'$addToSet': {'tasks.' + task_type: self.task['_id']}})
                return self.send_data_response()

            if self.data.get('submit'):  # 提交任务
                b_field = self.get_base_field(task_type)
                source = self.prop(self.task, 'params.source')
                base_txts = [t['txt'] for t in self.task['base_txts']]
                cond.update({'source': source, b_field: {'$in': base_txts}, 'sc': {'$ne': 39}})
                if self.db.char.find_one(cond):  # sc为39（即三字相同）的字数据可以忽略
                    return self.send_error_response(e.task_submit_error, message='还有未提交的字图，不能提交任务')
                used_time = (self.now() - self.task['picked_time']).total_seconds()
                self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                    'status': self.STATUS_FINISHED, 'finished_time': self.now(), 'used_time': used_time}})

            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
