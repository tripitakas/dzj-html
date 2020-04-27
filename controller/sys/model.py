#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.model import Model
from controller.page.api import PageTaskPublishApi


class Log(Model):
    collection = 'log'
    fields = [
        {'id': 'op_type', 'name': '类型'},
        {'id': 'target_id', 'name': '对象id'},
        {'id': 'content', 'name': '内容'},
        {'id': 'remark', 'name': '备注'},
        {'id': 'create_time', 'name': '创建时间'},
    ]
    primary = '_id'

    search_tips = '请搜索类型'
    search_fields = ['op_type', 'username', 'remark']
    op_types = {
        'gen_chars': '生成字表',
    }

    @classmethod
    def get_type_name(cls, op_type):
        return cls.op_types.get(op_type) or op_type


class Oplog(Model):
    collection = 'oplog'
    fields = [
        {'id': 'op_type', 'name': '类型'},
        {'id': 'status', 'name': '状态'},
        {'id': 'content', 'name': '内容'},
        {'id': 'create_by', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
    ]
    primary = '_id'

    search_tips = '请搜索类型'
    search_fields = ['op_type']
    statuses = {
        'ongoing': '进行中',
        'finished': '已完成',
    }

    op_types = {
        'gen_chars': '生成字表',
        'extract_img': '生成字图',
        'publish_task': '发布任务',
    }

    field_names = {
        'valid_pages': '有效页码',
        'invalid_pages': '无效页码',
        'inserted_char': '已插入字码',
        'existed_char': '已存在字码',
        'invalid_char': '无效字码',
        'cut_char_success': '字图生成成功',
        'cut_char_failed': '字图生成失败',
        'cut_char_existed': '字图已存在',
        'cut_column_success': '列图生成成功',
        'cut_column_failed': '列图生成失败',
        'task_type': '任务类型',
        'task_params': '任务参数',
        **PageTaskPublishApi.field_names,
    }

    @classmethod
    def get_type_name(cls, op_type):
        return cls.op_types.get(op_type) or op_type

    @classmethod
    def get_status_name(cls, status):
        return cls.statuses.get(status) or status

    @classmethod
    def get_field_name(cls, field):
        name = cls.field_names.get(field)
        return name or super().get_field_name(field)
