#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from controller import errors as e
from controller import helper as h
from controller import validate as v
from controller.char.base import CharHandler


class CharTaskPublishApi(CharHandler):
    URL = r'/api/char/task/publish'

    def post(self):
        """发布字任务"""
        try:
            rules = [(v.not_empty, 'batch', 'task_type', 'source')]
            self.validate(self.data, rules)
            if not self.db.char.find_one({'source': self.data['source']}):
                self.send_error_response(e.no_object, message='没有找到%s相关的字数据' % self.data['batch'])

            source = self.data['source']
            task_type = self.data['task_type']
            num = int(self.data.get('num') or 1)
            # 检查是否已发布
            cond = {'task_type': task_type, 'num': num, 'params.source': source}
            if self.db.task.find_one(cond):
                msg = '数据分类 %s已发布过 %s#%s的任务' % (source, self.get_task_name(task_type), num)
                self.send_error_response(e.task_failed, message=msg)
            # 根据分类统计字种，发布任务
            pub_time = self.now()
            normal_txts, rare_txts = self.get_base_txts(self.db, source, task_type)
            tasks = [self.task_meta(task_type, t, source, pub_time) for t in (normal_txts + rare_txts)]
            self.db.task.insert_many(tasks)
            # 先返回客户端
            self.send_data_response(dict(normal_count=len(normal_txts), rare_count=len(rare_txts)))

            # 后更新txt_equals/tripitakas
            log = dict(task_type=task_type, normal_txts=normal_txts, rare_txts=rare_txts)
            self.add_op_log(self.db, 'publish_task', None, log, self.username)
            self.update_txt_equals(self.db, self.data['batch'], task_type)
            self.update_tripitakas(self.db, self.data['batch'], task_type)

        except self.DbError as error:
            return self.send_db_error(error)

    def task_meta(self, task_type, base_txts, source, pub_time=None):
        batch = self.data['batch']
        num = int(self.data.get('num') or 1)
        pre_tasks = self.data.get('pre_tasks') or []
        priority = int(self.data.get('priority') or 2)
        is_oriented = self.data.get('is_oriented') == '1'
        char_count = sum([t['count'] for t in base_txts])
        task = dict(task_type=task_type, num=num, batch=batch, status=self.STATUS_PUBLISHED, priority=priority,
                    steps={}, pre_tasks=pre_tasks, is_oriented=is_oriented, collection='char', id_name='name',
                    doc_id='', base_txts=base_txts, char_count=char_count, params=dict(source=source),
                    txt_equals={}, result={}, create_time=pub_time, updated_time=pub_time,
                    publish_time=pub_time, publish_user_id=self.user_id, publish_by=self.username)
        not is_oriented and task.pop('is_oriented', 0)
        return task

    @classmethod
    def get_base_txts(cls, db, source, task_type):
        """ 获取待发布任务的字种"""
        base_field = cls.get_base_field(task_type)  # cmb_txt/rvw_txt
        counts = list(db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + base_field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))
        # 统计常见字种
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_txts = [[{'txt': c['_id'], 'count': c['count']}] for c in counts1]
        # 统计生僻字种
        counts2 = [c for c in counts if c['count'] < 50]
        rare_txts, base_txts, total_count = [], [], 0
        for c in counts2:
            total_count += c['count']
            base_txts.append({'txt': c['_id'], 'count': c['count']})
            if total_count >= 50 or len(base_txts) >= 10:
                rare_txts.append(base_txts)
                base_txts, total_count = [], 0  # reset
        total_count and rare_txts.append(base_txts)

        return normal_txts, rare_txts


class CharTaskClusterApi(CharHandler):
    URL = '/api/task/(do|update|nav)/@char_task/@task_id'

    def post(self, mode, task_type, task_id):
        """提交聚类校对任务"""
        try:
            update = {'updated_time': self.now()}
            user_level = self.get_user_txt_level(self, task_type)
            cond = {'tasks.' + task_type: {'$ne': self.task['_id']}, 'txt_level': {'$lte': user_level}}
            if self.data.get('char_names'):  # 提交单页
                cond.update({'name': {'$in': self.data.get('char_names')}})
                self.db.char.update_many(cond, {'$addToSet': {'tasks.' + task_type: self.task['_id']}})
                self.send_data_response()
                return self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})

            if self.data.get('submit') and self.task['status'] != self.STATUS_FINISHED:  # 提交任务
                b_field = self.get_base_field(task_type)
                source = self.prop(self.task, 'params.source')
                base_txts = [t['txt'] for t in self.task['base_txts']]
                cond.update({'source': source, b_field: {'$in': base_txts}, 'sc': {'$ne': 39}})
                if self.db.char.find_one(cond):  # 检查sc不为39（即三字相同）的字数据
                    return self.send_error_response(e.task_submit_error, message='还有未提交的字图，不能提交任务')
                used_time = (self.now() - self.task['picked_time']).total_seconds()
                update.update({'status': self.STATUS_FINISHED, 'finished_time': self.now(), 'used_time': used_time})
                self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})

            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
