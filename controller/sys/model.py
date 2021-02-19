#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.model import Model
from controller.page.api_task import PageTaskPublishApi


class Log(Model):
    primary = '_id'
    collection = 'log'
    fields = {
        'content': {'name': '内容'},
        'op_type': {'name': '类型'},
        'target_id': {'name': '对象id'},
        'create_time': {'name': '创建时间'},
        'remark': {'name': '备注'},
    }
    op_types = {'gen_chars': '生成字表'}

    @classmethod
    def get_type_name(cls, op_type):
        return cls.op_types.get(op_type) or op_type


class Oplog(Model):
    primary = '_id'
    collection = 'oplog'
    statuses = {
        'ongoing': '进行中',
        'finished': '已完成',
    }
    op_types = {
        'gen_chars': '生成字表',
        'extract_img': '生成字图',
        'publish_task': '发布任务',
        'check_match': '检查图文匹配',
        'find_cmp': '寻找比对文本',
    }
    field_names = {
        'task_type': '任务类型',
        'task_params': '任务参数',
        'valid_pages': '有效页码',
        'invalid_char': '无效字码',
        'invalid_pages': '无效页码',
        'updated_char': '已更新字码',
        'inserted_char': '已插入字码',
        'cut_char_existed': '字图已存在',
        'cut_char_failed': '字图生成失败',
        'cut_char_success': '字图生成成功',
        'cut_column_failed': '列图生成失败',
        'cut_column_success': '列图生成成功',
        'match': '匹配',
        'mis_match': '不匹配',
        'matched_before': '曾匹配',
        **PageTaskPublishApi.field_names(),
    }
    fields = {
        'status': {'name': '状态', 'filter': statuses},
        'op_type': {'name': '类型', 'filter': op_types},
        'content': {'name': '内容'},
        'create_by': {'name': '创建人'},
        'create_time': {'name': '创建时间'},
    }
    search_fields = ['op_type']

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
