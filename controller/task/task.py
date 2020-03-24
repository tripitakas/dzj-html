#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础表。
@time: 2019/10/16
"""
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
        {'id': 'params', 'name': '输入参数'},
        {'id': 'result', 'name': '输出结果'},
        {'id': 'char_count', 'name': '单字总数'},
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
    ]

    # 任务类型定义
    # pre_tasks：默认的前置任务
    # data.collection：任务所对应数据表
    # data.id：数据表的主键名称
    # data.input_field：任务所依赖的数据字段。如果该字段不为空，则可以发布任务
    # data.output_field：任务输出的字段。如果该字段不为空，则表示任务已完成
    # data.shared_field：任务共享和保护的数据字段
    task_types = {
        'import_image': {
            'name': '导入图片',
        },
        'upload_cloud': {
            'name': '上传云端',
            'data': {'collection': 'page', 'id': 'name', 'output_field': 'img_cloud_path'},
        },
        'ocr_box': {
            'name': 'OCR字框',
            'data': {'collection': 'page', 'id': 'name'},
        },
        'cut_proof': {
            'name': '切分校对', 'pre_tasks': ['ocr_box', 'upload_cloud'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['box', '字框'], ['order', '字序']],
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['box', '字框'], ['order', '字序']],
        },
        'ocr_text': {
            'name': 'OCR文字', 'pre_tasks': ['cut_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'box'},
        },
        'text_proof_1': {
            'name': '文字校一', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select', '选择比对文本'], ['proof', '校对']],
        },
        'text_proof_2': {
            'name': '文字校二', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select', '选择比对文本'], ['proof', '校对']],
        },
        'text_proof_3': {
            'name': '文字校三', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select', '选择比对文本'], ['proof', '校对']],
        },
        'text_review': {
            'name': '文字审定', 'pre_tasks': ['text_proof_1', 'text_proof_2', 'text_proof_3'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
        'text_hard': {
            'name': '难字处理', 'pre_tasks': ['text_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
        'cluster_proof': {'name': '聚类校对', 'data': {'collection': 'char', 'id': 'name'}, 'num': [1, 2, 3]},
        'cluster_review': {'name': '聚类审定', 'data': {'collection': 'char', 'id': 'name'}},
        'separate_proof': {'name': '分类校对', 'data': {'collection': 'char', 'id': 'name'}, 'num': [1, 2, 3]},
        'separate_review': {'name': '分类审定', 'data': {'collection': 'char', 'id': 'name'}},
    }

    # 其它任务定义
    # 1. groups表示组任务，对于同一数据的一组任务而言，用户只能领取其中的一个。
    #    在任务大厅和我的任务中，任务组中的任务将合并显示。 组任务仅在以上两处起作用，不影响其他任务管理功能。
    # 2. 数据编辑伪任务。数据编辑需要仿照任务，按照一定的步骤进行。在这里定义。
    task_extras = {
        'text_proof': {
            'name': '文字校对',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select', '选择比对文本'], ['proof', '校对']],
            'groups': ['text_proof_1', 'text_proof_2', 'text_proof_3']
        },
        'cut_edit': {
            'name': '切分修改',
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'box'},
            'steps': [['box', '字框'], ['order', '字序']],
        },
        'cut_view': {
            'name': '切分查看',
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'box'},
            'steps': [['box', '字框'], ['order', '字序']],
        },
        'text_edit': {
            'name': '文字修改',
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
        'text_view': {
            'name': '文字查看',
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        }
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

    @classmethod
    def all_task_types(cls):
        task_types = cls.task_types.copy()
        task_types.update(cls.task_extras)
        return task_types

    @classmethod
    def is_group(cls, task_type):
        return 'groups' in h.prop(cls.all_task_types(), task_type)

    @classmethod
    def get_ocr_tasks(cls):
        """ 获取OCR任务类型，即小欧处理的任务"""
        return ['import_image', 'upload_cloud', 'ocr_box', 'ocr_text']

    @classmethod
    def get_task_types(cls, collection):
        return {t: v['name'] for t, v in cls.task_types.items() if h.prop(v, 'data.collection') == collection}

    @classmethod
    def get_task_meta(cls, task_type):
        return cls.all_task_types().get(task_type)

    @classmethod
    def get_data_conf(cls, task_type):
        d = h.prop(cls.all_task_types(), '%s.data' % task_type) or dict()
        return d.get('collection'), d.get('id'), d.get('input_field'), d.get('shared_field')

    @classmethod
    def get_shared_field(cls, task_type):
        return h.prop(cls.all_task_types(), '%s.data.shared_field' % task_type)

    @classmethod
    def get_data_collection(cls, task_type):
        return h.prop(cls.all_task_types(), '%s.data.collection' % task_type)

    @classmethod
    def get_pre_tasks(cls, task_type):
        return h.prop(cls.all_task_types(), task_type + '.pre_tasks', [])

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.all_task_types().items()}

    @classmethod
    def get_task_name(cls, task_type):
        return cls.task_names().get(task_type) or task_type

    @classmethod
    def get_steps(cls, task_type):
        steps = h.prop(cls.all_task_types(), '%s.steps' % task_type, [])
        return [s[0] for s in steps] if steps else []

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
        if key == 'status':
            return cls.get_status_name(value)
        if key == 'pre_tasks':
            return '/'.join([cls.get_task_name(t) for t in value])
        if key == 'steps':
            return '/'.join([cls.get_step_name(t) for t in value.get('todo', [])])
        if key == 'priority':
            return cls.get_priority_name(int(value or 0))
        return h.format_value(value, key, doc)

    @classmethod
    def get_task_search_condition(cls, request_query, collection=None, mode=None):
        """ 获取任务的查询条件"""
        condition, params = dict(collection=collection) if collection else dict(), dict()
        value = h.get_url_param('txt_kind', request_query)
        if value:
            params['txt_kind'] = value
            condition.update({'$or': [{'params.ocr_txt': value}]})
        for field in ['task_type', 'collection', 'status', 'priority']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['batch', 'doc_id', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
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
            condition['picked_time'] = {'$gt': datetime.strptime(finished_start, '%Y-%m-%d %H:%M:%S')}
        finished_end = h.get_url_param('finished_end', request_query)
        if finished_end:
            params['finished_end'] = finished_end
            condition['finished_time'] = condition.get('finished_time') or {}
            condition['finished_time'].update({'$lt': datetime.strptime(finished_end, '%Y-%m-%d %H:%M:%S')})
        if mode == 'browse':  # 浏览模式过滤掉小欧任务
            condition['task_type'] = {'$nin': cls.get_ocr_tasks()}
        return condition, params
