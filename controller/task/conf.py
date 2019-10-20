#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务配置表。
@time: 2019/10/16
"""
from controller import errors


class TaskConfig(object):
    # 任务类型定义表。
    # pre_tasks：默认的前置任务
    # data.collection：任务所对应数据表
    # data.id：数据表的主键名称
    # data.input_field：该任务依赖的数据字段，该字段就绪，则可以发布任务
    # data.shared_field：该任务共享和保护的数据字段
    task_types = {
        'cut_proof': {
            'name': '切分校对',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['char_box', '字框'], ['block_box', '栏框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['char_box', '字框'], ['block_box', '栏框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'text_proof_1': {
            'name': '文字校一',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_2': {
            'name': '文字校二',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_3': {
            'name': '文字校三',
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

    # 任务组定义表。
    # 对于同一数据的一组任务而言，用户只能领取其中的一个。
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

    """ 数据锁介绍
    1）数据锁的目的：通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
      1.tasks。同一数据的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
      2.roles。数据专家角色对所有page的授权字段
    2）数据锁的类型：
      1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
      2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时分配临时数据锁，在窗口离开时解锁，或定时自动回收。
    3）数据锁的使用：
      1.首先在task_shared_data_fields中注册需要共享的数据字段；
      2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
    4) 数据锁的存储：存储在数据记录的lock字段中。比如page表的数据锁，就存在page表的lock字段中。
    """
    # 数据锁权限配置表。在对共享数据进行写操作时，需要检查数据锁资质，以这个表来判断。
    # tasks: 共享字段授权的任务，仅对同一份数据有效
    # roles: 共享字段授权的角色，对所有数据有效
    data_auth_maps = {
        'box': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['chars', 'columns', 'blocks'],
            'tasks': ['cut_proof', 'cut_review', 'text_proof', 'text_review', 'text_hard'],
            'roles': ['切分专家']
        },
        'text': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['text', 'txt_html'],
            'tasks': ['text_review', 'text_hard'],
            'roles': ['文字专家']
        },
    }

    @classmethod
    def prop(cls, obj, key):
        for s in key.split('.'):
            obj = obj.get(s) if isinstance(obj, dict) else None
        return obj

    @classmethod
    def all_task_types(cls):
        task_types = cls.task_types.copy()
        task_types.update(cls.task_groups)
        return task_types

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

    @classmethod
    def get_task_meta(cls, task_type):
        d = cls.all_task_types().get(task_type)['data']
        return d['collection'], d['id'], d.get('input_field'), d.get('shared_field')

    @classmethod
    def init_steps(cls, task, mode, cur_step=''):
        """ 检查当前任务的步骤，缺省时进行设置，有误时报错 """
        todo = cls.prop(task, 'steps.todo') or []
        submitted = cls.prop(task, 'steps.submitted') or []
        un_submitted = [s for s in todo if s not in submitted]
        if not todo:
            return errors.task_steps_is_empty
        if cur_step and cur_step not in todo:
            return errors.task_step_error
        if not cur_step:
            cur_step = un_submitted[0] if mode == 'do' else todo[0]

        steps = dict()
        index = todo.index(cur_step)
        steps['current'] = cur_step
        steps['is_first'] = index == 0
        steps['is_last'] = index == len(todo) - 1
        steps['prev'] = todo[index - 1] if index > 0 else None
        steps['next'] = todo[index + 1] if index < len(todo) - 1 else None
        return steps

    @classmethod
    def get_shared_field(cls, task_type):
        """ 获取任务保护的共享字段 """
        return cls.prop(cls.task_types, '%s.data.shared_field' % task_type)
