#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础表。
@time: 2019/10/16
"""
from datetime import datetime
from controller.model import Model
from controller.helper import prop
from controller.helper import get_date_time


class Task(Model):
    """ 数据库定义"""
    collection = 'task'
    primary = '_id'
    fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'collection', 'name': '数据表'},
        {'id': 'id_name', 'name': '主键名'},
        {'id': 'doc_id', 'name': '数据ID'},
        {'id': 'status', 'name': '状态'},
        {'id': 'priority', 'name': '优先级'},
        {'id': 'steps', 'name': '步骤'},
        {'id': 'pre_tasks', 'name': '前置任务'},
        {'id': 'input', 'name': '输入参数'},
        {'id': 'result', 'name': '输出结果'},
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
            'steps': [['blocks', '栏框'], ['chars', '字框'], ['columns', '列框'], ['orders', '字序']],
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['blocks', '栏框'], ['chars', '字框'], ['columns', '列框'], ['orders', '字序']],
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
            'name': '难字审定', 'pre_tasks': ['text_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
    }

    # 任务组定义。对于同一数据的一组任务而言，用户只能领取其中的一个。
    # 在任务大厅和我的任务中，任务组中的任务将合并显示。
    # 任务组仅在以上两处起作用，不影响其他任务管理功能。
    task_groups = {
        'text_proof': {
            'name': '文字校对',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select', '选择比对文本'], ['proof', '校对']],
            'groups': ['text_proof_1', 'text_proof_2', 'text_proof_3']
        },
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
        task_types.update(cls.task_groups)
        return task_types

    @classmethod
    def is_group(cls, task_type):
        return 'groups' in prop(cls.all_task_types(), task_type)

    @classmethod
    def get_doc_tasks(cls, collection):
        return {t: v['name'] for t, v in cls.task_types.items() if prop(v, 'data.collection') == collection}

    @classmethod
    def get_task_meta(cls, task_type):
        return cls.all_task_types().get(task_type)

    @classmethod
    def get_data_conf(cls, task_type):
        d = prop(cls.all_task_types(), '%s.data' % task_type) or dict()
        return d.get('collection'), d.get('id'), d.get('input_field'), d.get('shared_field')

    @classmethod
    def get_shared_field(cls, task_type):
        return prop(cls.task_types, '%s.data.shared_field' % task_type)

    @classmethod
    def get_data_collection(cls, task_type):
        return prop(cls.task_types, '%s.data.collection' % task_type)

    @classmethod
    def get_task_steps(cls, task_type):
        return prop(cls.all_task_types(), task_type + '.steps', [])

    @classmethod
    def get_pre_tasks(cls, task_type):
        return prop(cls.all_task_types(), task_type + '.pre_tasks', [])

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.all_task_types().items()}

    @classmethod
    def get_task_name(cls, task_type):
        return cls.task_names().get(task_type) or task_type

    @classmethod
    def get_steps(cls, task_type):
        steps = prop(cls.all_task_types(), '%s.steps' % task_type, [])
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
    def format_value(cls, value, key=None):
        """ 格式化任务信息"""
        if key == 'task_type':
            value = cls.get_task_name(value)
        elif key == 'status':
            value = cls.get_status_name(value)
        elif key == 'pre_tasks':
            value = '/'.join([cls.get_task_name(t) for t in value])
        elif key == 'steps':
            value = '/'.join([cls.get_step_name(t) for t in value.get('todo', [])])
        elif key == 'priority':
            value = cls.get_priority_name(int(value))
        elif isinstance(value, datetime):
            value = get_date_time('%Y-%m-%d %H:%M', value)
        elif isinstance(value, dict):
            value = value.get('error') or value.get('message') or \
                    '<br/>'.join(['%s: %s' % (k, v) for k, v in value.items()])
        return value or ''

    @classmethod
    def get_status_name(cls, status):
        return cls.task_statuses.get(status) or status

    @classmethod
    def get_priority_name(cls, priority):
        return cls.priorities.get(priority) or priority
