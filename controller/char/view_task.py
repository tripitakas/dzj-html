#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from bson import json_util
from datetime import datetime
from operator import itemgetter
from controller import errors as e
from controller.task.task import Task
from controller.char.char import Char
from controller.task.base import TaskHandler
from controller.char.base import CharHandler


class CharTaskListHandler(TaskHandler, Char):
    URL = '/char/task/list'

    page_title = '字任务管理'
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型', 'filter': CharHandler.task_names('char')},
        {'id': 'num', 'name': '校次'},
        {'id': 'base_txts', 'name': '聚类字种'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'status', 'name': '状态', 'filter': CharHandler.task_statuses},
        {'id': 'priority', 'name': '优先级', 'filter': CharHandler.priorities},
        {'id': 'is_oriented', 'name': '是否定向', 'filter': CharHandler.yes_no},
        {'id': 'txt_equals', 'name': '相同程度'},
        {'id': 'params', 'name': '输入参数'},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'used_time', 'name': '执行时间(分)'},
        {'id': 'remark', 'name': '管理备注'},
        {'id': 'my_remark', 'name': '用户备注'},

    ]
    search_fields = ['batch', 'remark']
    hide_fields = ['_id', 'txt_equals', 'params', 'return_reason', 'create_time', 'updated_time',
                   'publish_by', 'remark']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/task/delete'},
        {'operation': 'btn-dashboard', 'label': '综合统计'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'batch', 'label': '按批次'},
            {'operation': 'picked_user_id', 'label': '按用户'},
            {'operation': 'task_type', 'label': '按类型'},
            {'operation': 'status', 'label': '按状态'},
        ]},
        {'operation': 'btn-more', 'label': '更多操作', 'groups': [
            {'operation': 'bat-batch', 'label': '更新批次'},
            {'operation': 'bat-assign', 'label': '批量指派'},
        ]},
    ]
    actions = [
        {'action': 'btn-browse', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs()
        if self.get_hide_fields() is not None:
            kwargs['hide_fields'] = self.get_hide_fields()
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:  # 任务浏览员
            kwargs['actions'] = [{'action': 'btn-browse', 'label': '浏览'}]
            kwargs['operations'] = [{'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'}]
        return kwargs

    def format_value(self, value, key=None, doc=None):
        """格式化page表的字段输出"""
        if key == 'params' and value:
            names = dict(source='来源', txt_kinds='校对字头')
            return '<br/>'.join(['%s: %s' % (names.get(k) or k, v) for k, v in value.items()])
        if key == 'txt_equals' and value:
            return '<br/>'.join(['%s: %s' % (Char.equal_level.get(k) or k, v) for k, v in value.items()])
        return super().format_value(value, key, doc)

    def get(self):
        """任务管理-字任务管理"""
        try:
            kwargs = self.get_template_kwargs()
            cond, params = self.get_task_search_condition(self.request.query, 'char')
            docs, pager, q, order = Task.find_by_page(self, cond, self.search_fields, '-_id')
            self.render('char_task_list.html', docs=docs, pager=pager, order=order, q=q, params=params,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CharTaskStatHandler(CharHandler):
    URL = '/char/task/statistic'

    def get(self):
        """根据用户、批次、类型或状态进行统计"""
        try:
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status', 'batch']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、批次、任务类型或任务状态统计')

            counts = list(self.db.task.aggregate([
                {'$match': self.get_task_search_condition(self.request.query, 'char')[0]},
                {'$group': {'_id': '$%s' % kind, 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))

            head, rows = [], []
            if kind == 'picked_user_id':
                head = ['分组', '用户', '数量']
                users = list(self.db.user.find({'_id': {'$in': [c['_id'] for c in counts]}}))
                users = {u['_id']: [u.get('group') or '', u.get('name')] for u in users}
                rows = [[*users.get(c['_id'], ['', '']), c['count']] for c in counts]
                rows.sort(key=itemgetter(1))
            elif kind == 'task_type':
                head = ['任务类型', '数量']
                rows = [[self.task_types[c['_id']]['name'] or c['_id'], c['count']] for c in counts]
            elif kind == 'status':
                head = ['任务状态', '数量']
                rows = [[self.task_statuses['_id'], c['count']] for c in counts]
            elif kind == 'batch':
                head = ['批次', '数量']
                rows = [[c['_id'], c['count']] for c in counts]
            total = sum([c['count'] for c in counts])

            self.render('task_statistic.html', collection='char', kind=kind, total=total, head=head, rows=rows,
                        title='字任务统计')

        except Exception as error:
            return self.send_db_error(error)


class CharTaskDashBoardHandler(CharHandler):
    URL = '/char/task/dashboard'

    def get(self):
        """综合统计"""
        from controller.page.view_task import PageTaskDashBoardHandler
        PageTaskDashBoardHandler.task_dashboard(self, 'char')


class CharTaskClusterHandler(CharHandler):
    URL = ['/task/@char_task/@task_id',
           '/api/task/@char_task/@task_id',
           '/task/do/@char_task/@task_id',
           '/task/nav/@char_task/@task_id',
           '/task/browse/@char_task/@task_id',
           '/task/update/@char_task/@task_id']

    def get(self, task_type, task_id):
        """聚类校对页面"""
        try:
            debug, start = False, self.now()
            data, task_cond, cond = self.get_chars(task_type)
            debug and print('[1]get chars:', (self.now() - start).total_seconds(), cond)

            txt = self.get_query_argument('txt', '')
            txt_equals = self.task.get('txt_equals') or {}

            self.render('char_cluster.html', Char=Char, **data, cur_txt=txt, readonly=self.readonly,
                        mode=self.mode, txt_equals=txt_equals, equal_level=self.equal_level,
                        page_title=self.get_task_name(task_type),
                        char_count=self.task.get('char_count'))

            if self.mode in ['do', 'update', 'nav']:  # 更新校对字头
                counts = list(self.db.char.aggregate([
                    {'$match': task_cond}, {'$group': {'_id': '$txt', 'count': {'$sum': 1}}},
                ]))
                txt_kinds = [c['_id'] for c in sorted(counts, key=itemgetter('count'), reverse=True)]
                self.db.task.update_one({'_id': self.task['_id']}, {'$set': {'params.txt_kinds': txt_kinds}})
                debug and print('[2]aggregate txt kinds:', (self.now() - start).total_seconds(), task_cond)

        except Exception as error:
            return self.send_db_error(error)

    def post(self, task_type, task_id):
        """聚类校对ajax获取数据"""
        try:
            if self.data.get('query') == 'txt_kinds':
                data = dict(txt_kinds=self.prop(self.task, 'params.txt_kinds', []))
            else:
                data = self.get_chars(task_type)[0]
            self.send_data_response(data)

        except Exception as error:
            return self.send_db_error(error)

    def get_chars(self, task_type):
        b_field = self.get_base_field(task_type)
        source = self.prop(self.task, 'params.source')
        base_txts = [t['txt'] for t in self.task['base_txts']]
        task_cond = {'source': source, b_field: {'$in': base_txts} if len(base_txts) > 1 else base_txts[0]}
        cond = self.get_user_filter(task_type)
        cond.update(task_cond)
        # 做任务时，限制每页字数
        self.page_size = int(json_util.loads(self.get_secure_cookie('cluster_page_size') or '50'))
        self.page_size = 100 if self.page_size > 100 and self.mode in ['do', 'update'] else self.page_size
        chars, pager, q, order = Char.find_by_page(self, cond, default_order=[('pc', 1), ('cc', 1)])
        for ch in chars:  # 设置单字列图
            column_name = '%s_%s' % (ch['page_name'], self.prop(ch, 'column.cid'))
            ch['column']['img_url'] = self.get_web_img(column_name, 'column')
            ch['img_url'] = self.get_char_img(ch)
        txt_kinds = self.prop(self.task, 'params.txt_kinds') or base_txts
        data = dict(chars=chars, pager=pager, q=q, order=order, base_txts=base_txts, txt_kinds=txt_kinds)
        return data, task_cond, cond
