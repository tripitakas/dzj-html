#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础表
@time: 2019/10/16
"""
import re
from datetime import datetime
from bson.objectid import ObjectId
from controller.model import Model
from controller import helper as h


class Task(Model):
    """ 数据库定义"""
    collection = 'task'
    primary = '_id'
    fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'num', 'name': '校次'},
        {'id': 'collection', 'name': '数据表'},
        {'id': 'id_name', 'name': '主键名'},
        {'id': 'doc_id', 'name': '数据ID'},
        {'id': 'status', 'name': '状态'},
        {'id': 'priority', 'name': '优先级'},
        {'id': 'steps', 'name': '步骤'},
        {'id': 'pre_tasks', 'name': '前置任务'},
        {'id': 'is_oriented', 'name': '是否定向'},
        {'id': 'params', 'name': '输入参数'},
        {'id': 'result', 'name': '输出结果'},
        {'id': 'txt_kind', 'name': '字种'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'required_count', 'name': '需要校对数量'},
        {'id': 'type_tips', 'name': '类型说明'},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_user_id', 'name': '发布人id'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_user_id', 'name': '领取人id'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'is_sample', 'name': '示例任务'},
        {'id': 'remark', 'name': '备注'},
        {'id': 'message', 'name': '日志'},
    ]

    # 任务类型定义
    task_types = {
        'import_image': {
            'name': '导入图片', 'publishable': True,
        },
        'cut_proof': {
            'name': '切分校对', 'data': {'collection': 'page', 'id': 'name'},
            'steps': [['box', '字框'], ['order', '字序']],
            'num': [1, 2, 3, 4, 5, 6], 'publishable': True,
        },
        'cut_review': {
            'name': '切分审定', 'data': {'collection': 'page', 'id': 'name'},
            'steps': [['box', '字框'], ['order', '字序']],
            'num': [1, 2, 3, 4, 5, 6], 'pre_tasks': ['cut_proof'], 'publishable': True,
        },
        'upload_cloud': {
            'name': '上传云端', 'data': {'collection': 'page', 'id': 'name'},
            'publishable': True, 'is_sys_task': True,
        },
        'ocr_box': {
            'name': 'OCR切分', 'data': {'collection': 'page', 'id': 'name'},
            'num': [1, 2, 3, 4, 5, 6], 'publishable': True, 'is_sys_task': True,
        },
        'ocr_text': {
            'name': 'OCR文字', 'data': {'collection': 'page', 'id': 'name'},
            'num': [1, 2, 3, 4, 5, 6], 'publishable': True, 'is_sys_task': True,
        },
        # 'txt_match': {
        #     'name': '图文匹配', 'data': {'collection': 'page', 'id': 'name'},
        #     'publishable': False, 'remark': '不要设置校次，以免影响field字段',
        # },
        'text_proof': {
            'name': '文字校对', 'data': {'collection': 'page', 'id': 'name'},
            'num': [1, 2, 3, 4, 5, 6], 'pre_tasks': ['cut_review'], 'publishable': True,
        },
        'text_review': {
            'name': '文字审定', 'data': {'collection': 'page', 'id': 'name'},
            'num': [1, 2, 3, 4, 5, 6], 'pre_tasks': ['text_proof'], 'publishable': True,
        },
        'cluster_proof': {
            'name': '聚类校对', 'data': {'collection': 'char', 'id': 'name'},
            'num': [1, 2, 3, 4, 5, 6], 'publishable': True,
        },
        'cluster_review': {
            'name': '聚类审定', 'data': {'collection': 'char', 'id': 'name'},
            'num': [1, 2, 3], 'pre_tasks': ['cluster_proof'], 'publishable': True,
        },
        # 'rare_proof': {
        #     'name': '生僻校对', 'data': {'collection': 'char', 'id': 'name'},
        #     'num': [1, 2, 3, 4, 5, 6], 'publishable': False,
        # },
        # 'rare_review': {
        #     'name': '生僻审定', 'data': {'collection': 'char', 'id': 'name'},
        #     'num': [1, 2, 3], 'pre_tasks': ['cluster_proof'], 'publishable': False,
        # },
    }

    # 任务状态表
    STATUS_PUBLISHED = 'published'
    STATUS_PENDING = 'pending'
    STATUS_FETCHED = 'fetched'
    STATUS_PICKED = 'picked'
    STATUS_FAILED = 'failed'
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    task_statuses = {
        STATUS_PUBLISHED: '已发布未领取', STATUS_PENDING: '等待前置任务', STATUS_FETCHED: '已获取',
        STATUS_PICKED: '进行中', STATUS_FAILED: '失败', STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    # 任务优先级
    priorities = {3: '高', 2: '中', 1: '低'}
    yes_no = {True: '是', False: '否'}

    @classmethod
    def has_num(cls, task_type):
        num = cls.prop(cls.task_types, task_type + '.num')
        return num is not None

    @classmethod
    def get_page_tasks(cls):
        return {k: t for k, t in cls.task_types.items() if cls.prop(t, 'data.collection') == 'page'}

    @classmethod
    def get_char_tasks(cls):
        return {k: t for k, t in cls.task_types.items() if cls.prop(t, 'data.collection') == 'char'}

    @classmethod
    def task_names(cls, collection=None, publishable=None, include_sys_task=False):
        r = cls.task_types
        if collection:
            r = {k: t for k, t in r.items() if cls.prop(t, 'data.collection') == collection}
        if publishable is not None:
            r = {k: t for k, t in r.items() if t.get('publishable') == publishable}
        if not include_sys_task:
            r = {k: t for k, t in r.items() if t.get('is_sys_task') in [None, False]}
        return {k: t['name'] for k, t in r.items()}

    @classmethod
    def step_names(cls):
        step_names = dict()
        for t in cls.task_types.values():
            for step in t.get('steps', []):
                step_names.update({step[0]: step[1]})
        return step_names

    @classmethod
    def get_step_name(cls, step):
        return cls.step_names().get(step) or step

    @classmethod
    def get_task_name(cls, task_type):
        name = h.prop(cls.task_types, '%s.name' % task_type.split('#')[0]) or task_type
        if len(task_type.split('#')) > 1:
            name += '#' + task_type.split('#')[-1]
        return name

    @classmethod
    def get_status_name(cls, status):
        return cls.task_statuses.get(status) or status

    @classmethod
    def get_priority_name(cls, priority):
        return cls.priorities.get(priority) or priority

    @classmethod
    def format_value(cls, value, key=None, doc=None):
        """ 格式化task表的字段输出"""
        if key == 'task_type':
            return cls.get_task_name(value)
        if key == 'status' and value:
            return cls.get_status_name(value)
        if key == 'pre_tasks' and value:
            return '/'.join([cls.get_task_name(t) for t in value])
        if key == 'steps' and value:
            return '/'.join([cls.get_step_name(t) for t in value.get('todo', [])])
        if key == 'priority' and value:
            return cls.get_priority_name(int(value or 0))
        if key == 'is_oriented':
            return cls.yes_no.get(value) or '否'
        return h.format_value(value, key, doc)

    @classmethod
    def get_task_search_condition(cls, request_query, collection=None):
        """ 获取任务的查询条件"""
        # request_query = re.sub('[?&]?from=.*$', '', request_query)
        condition, params = dict(collection=collection) if collection else dict(), dict()
        for field in ['task_type', 'collection', 'status', 'priority', 'txt_kind', 'is_oriented']:
            value = h.get_url_param(field, request_query)
            if value not in ['', None]:
                params[field] = value
                value = int(value) if field == 'priority' else value
                value = None if field == 'is_oriented' and not value else value
                condition.update({field: value})
        for field in ['batch', 'doc_id', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m = re.match(r'["\'](.*)["\']', value)
                condition.update({field: m.group(1) if m else {'$regex': value}})
        picked_user_id = h.get_url_param('picked_user_id', request_query)
        if picked_user_id:
            params['picked_user_id'] = picked_user_id
            condition.update({'picked_user_id': ObjectId(picked_user_id)})

        publish_start = h.get_url_param('publish_start', request_query)
        if publish_start:
            params['publish_start'] = publish_start
            condition['publish_time'] = {'$gt': datetime.strptime(publish_start, '%Y-%m-%d %H:%M:%S')}
        publish_end = h.get_url_param('publish_end', request_query)
        if publish_end:
            params['publish_end'] = publish_end
            condition['publish_time'] = condition.get('publish_time') or {}
            condition['publish_time'].update({'$lt': datetime.strptime(publish_end, '%Y-%m-%d %H:%M:%S')})

        picked_start = h.get_url_param('picked_start', request_query)
        if picked_start:
            params['picked_start'] = picked_start
            condition['picked_time'] = {'$gt': datetime.strptime(picked_start, '%Y-%m-%d %H:%M:%S')}
        picked_end = h.get_url_param('picked_end', request_query)
        if picked_end:
            params['picked_end'] = picked_end
            condition['picked_time'] = condition.get('picked_time') or {}
            condition['picked_time'].update({'$lt': datetime.strptime(picked_end, '%Y-%m-%d %H:%M:%S')})

        finished_start = h.get_url_param('finished_start', request_query)
        if finished_start:
            params['finished_start'] = finished_start
            condition['finished_time'] = {'$gt': datetime.strptime(finished_start, '%Y-%m-%d %H:%M:%S')}
        finished_end = h.get_url_param('finished_end', request_query)
        if finished_end:
            params['finished_end'] = finished_end
            condition['finished_time'] = condition.get('finished_time') or {}
            condition['finished_time'].update({'$lt': datetime.strptime(finished_end, '%Y-%m-%d %H:%M:%S')})

        updated_start = h.get_url_param('updated_start', request_query)
        if updated_start:
            params['updated_start'] = updated_start
            condition['updated_time'] = {'$gt': datetime.strptime(updated_start, '%Y-%m-%d %H:%M:%S')}
        updated_end = h.get_url_param('updated_end', request_query)
        if updated_end:
            params['updated_end'] = updated_end
            condition['updated_time'] = condition.get('updated_time') or {}
            condition['updated_time'].update({'$lt': datetime.strptime(updated_end, '%Y-%m-%d %H:%M:%S')})
        return condition, params
