#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础表。
@time: 2019/10/16
"""
from controller.helper import prop
from controller.model import Model
from controller import validate as v


class Task(Model):
    # 数据库定义
    collection = 'task'
    fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '任务批次'},
        {'id': 'task_type', 'name': '任务类型'},
        {'id': 'collection', 'name': '任务关联的文档集合'},
        {'id': 'id_name', 'name': '文档键名'},
        {'id': 'doc_id', 'name': '文档键值'},
        {'id': 'status', 'name': '任务状态'},
        {'id': 'priority', 'name': '任务优先级'},
        {'id': 'steps', 'name': '任务步骤'},
        {'id': 'pre_tasks', 'name': '前置任务'},
        {'id': 'lock', 'name': '数据锁'},
        {'id': 'input', 'name': '任务输入参数'},
        {'id': 'result', 'name': '任务输出结果'},
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
    ]
    rules = [
        (v.not_empty, 'task_type', 'name'),
    ]
    primary = '_id'

    # 前端列表页面定义
    search_fields = ['doc_id', 'batch']
    search_tip = '请搜索页编码或批次号'
    operations = [  # 列表包含哪些批量操作
        {'operation': 'bat-assign', 'label': '批量指派'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    actions = [  # 列表单条记录包含哪些操作
        {'action': 'btn-view', 'label': '查看'},
        {'action': 'btn-update', 'label': '修改'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    modal_fields = [
        {'id': 'batch', 'name': '任务批次'},
    ]

    @classmethod
    def get_field_name(cls, field):
        for f in cls.fields:
            if f['id'] == field:
                return f['name']

    # 任务类型定义
    # pre_tasks：默认的前置任务
    # data.id：数据表的主键名称
    # data.collection：任务所对应数据表
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
            'steps': [['block_box', '栏框'], ['char_box', '字框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['block_box', '栏框'], ['char_box', '字框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'ocr_text': {
            'name': 'OCR文字', 'pre_tasks': ['cut_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'box'},
        },
        'text_proof_1': {
            'name': '文字校一', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_2': {
            'name': '文字校二', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_3': {
            'name': '文字校三', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
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
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
            'groups': ['text_proof_1', 'text_proof_2', 'text_proof_3']
        },
    }

    @classmethod
    def all_task_types(cls):
        task_types = cls.task_types.copy()
        task_types.update(cls.task_groups)
        return task_types

    @classmethod
    def get_shared_field(cls, task_type):
        """ 获取任务保护的共享字段 """
        return prop(cls.task_types, '%s.data.shared_field' % task_type)

    @classmethod
    def get_task_meta(cls, task_type):
        return cls.all_task_types().get(task_type)

    @classmethod
    def get_task_data_conf(cls, task_type):
        d = prop(cls.all_task_types(), '%s.data' % task_type) or dict()
        return d.get('collection'), d.get('id'), d.get('input_field'), d.get('shared_field')

    @classmethod
    def get_page_tasks(cls):
        return [t for t, v in cls.task_types.items() if prop(v, 'data.collection') == 'page']

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.all_task_types().items()}

    @classmethod
    def get_task_name(cls, task_type):
        return cls.task_names().get(task_type)

    @classmethod
    def step_names(cls):
        step_names = dict()
        for t in cls.task_types.values():
            for step in t.get('steps', []):
                step_names.update({step[0]: step[1]})
        return step_names

    @classmethod
    def get_step_name(cls, step):
        return cls.step_names().get(step)

    # 任务状态表
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_FETCHED = 'fetched'  # 已获取。小欧获取任务后尚未进行确认时的状态
    STATUS_PICKED = 'picked'
    STATUS_FAILED = 'failed'  # 失败。小欧执行任务失败时的状态
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    task_status_names = {
        STATUS_OPENED: '已发布未领取', STATUS_PENDING: '等待前置任务', STATUS_FETCHED: '已获取',
        STATUS_PICKED: '进行中', STATUS_FAILED: '失败', STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    @classmethod
    def get_status_name(cls, status):
        return cls.task_status_names.get(status)

    # 任务优先级
    priority_names = {3: '高', 2: '中', 1: '低'}

    @classmethod
    def get_priority_name(cls, priority):
        return cls.priority_names.get(priority)
