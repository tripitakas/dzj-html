#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.l10n import _t
from controller import helper as h
from controller.model import Model


class Oplog(Model):
    collection = 'oplog'
    fields = [
        {'id': 'op_type', 'name': '类型'},
        {'id': 'content', 'name': '内容'},
        {'id': 'create_by', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
    ]
    primary = '_id'

    page_title = '管理日志'
    search_tips = '请搜索类型'
    search_fields = ['op_type']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    operations = [  # 列表包含哪些批量操作
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    img_operations = []
    info_fields = ['']
    actions = [  # 列表单条记录包含哪些操作
        {'action': 'my-view', 'label': '查看'},
        {'action': 'btn-remove', 'label': '删除'},
    ]

    @staticmethod
    def format_value(value, key=None, doc=None):
        if key == 'op_type':
            return _t(value)
        if key == 'content':
            return ', '.join(['<span class="key">%s</span>: <span class="value">%s</span>' % (
                _t(k), '%s%s' % (','.join(v[:10]), '...' if len(v) > 10 else '')
            ) for k, v in value.items()])
        return h.format_value(value, key, doc)
