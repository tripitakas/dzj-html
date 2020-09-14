#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from datetime import datetime
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller.page.view_task import PageTaskDashBoardHandler


class CharTaskListHandler(CharHandler):
    URL = '/char/task/list'

    page_title = '字任务管理'
    search_tips = '请搜索字种、批次号或备注'
    search_fields = ['params.ocr_txt', 'params.txt', 'batch', 'remark']
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'task_type', 'name': '类型', 'filter': CharHandler.task_names('char')},
        {'id': 'num', 'name': '校次'},
        {'id': 'txt_kind', 'name': '字种'},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'status', 'name': '状态', 'filter': CharHandler.task_statuses},
        {'id': 'priority', 'name': '优先级', 'filter': CharHandler.priorities},
        {'id': 'params', 'name': '输入参数'},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/task/delete'},
        {'operation': 'bat-assign', 'label': '批量指派', 'data-target': 'assignModal'},
        {'operation': 'bat-batch', 'label': '更新批次'},
        {'operation': 'btn-dashboard', 'label': '综合统计'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'picked_user_id', 'label': '按用户'},
            {'operation': 'task_type', 'label': '按类型'},
            {'operation': 'status', 'label': '按状态'},
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]
    hide_fields = ['_id', 'params', 'return_reason', 'create_time', 'updated_time', 'pre_tasks', 'publish_by', 'remark']
    update_fields = []

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs()
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:
            kwargs['actions'] = [{'action': 'btn-nav', 'label': '浏览'}]
            kwargs['operations'] = [{'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'}]
        return kwargs

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'txt_kind' and value:
            return (value[:5] + '...') if len(value) > 5 else value
        return super().format_value(value, key, doc)

    def get(self):
        """ 任务管理-字任务管理"""
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            condition, params = self.get_task_search_condition(self.request.query, 'char')
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id')
            self.render(
                'char_task_list.html', docs=docs, pager=pager, order=order, q=q, params=params,
                format_value=self.format_value, **kwargs,
            )
        except Exception as error:
            return self.send_db_error(error)


class CharTaskStatHandler(CharHandler):
    URL = '/char/task/statistic'

    def get(self):
        """ 根据用户、任务类型或任务状态统计页任务"""
        try:
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、任务类型或任务状态统计')

            counts = list(self.db.task.aggregate([
                {'$match': self.get_task_search_condition(self.request.query, 'char')[0]},
                {'$group': {'_id': '$%s' % kind, 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))

            trans = {}
            if kind == 'picked_user_id':
                users = list(self.db.user.find({'_id': {'$in': [c['_id'] for c in counts]}}))
                trans = {u['_id']: u['name'] for u in users}
            elif kind == 'task_type':
                trans = self.task_names()
            elif kind == 'status':
                trans = self.task_statuses
            label = dict(picked_user_id='用户', task_type='任务类型', status='任务状态')[kind]

            self.render('task_statistic.html', counts=counts, kind=kind, label=label, trans=trans, collection='char')

        except Exception as error:
            return self.send_db_error(error)


class CharTaskDashBoardHandler(CharHandler):
    URL = '/char/task/dashboard'

    def get(self):
        """ 综合统计"""
        PageTaskDashBoardHandler.task_dashboard(self, 'char')


class CharTaskClusterHandler(CharHandler):
    URL = ['/task/@cluster_task/@task_id',
           '/task/do/@cluster_task/@task_id',
           '/task/browse/@cluster_task/@task_id',
           '/task/update/@cluster_task/@task_id']

    config_fields = [
        {'id': 'page-size', 'name': '每页显示条数'},
        {'id': 'show-char-info', 'name': '是否显示字图信息', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'auto-pick', 'name': '提交后自动领新任务', 'input_type': 'radio', 'options': ['是', '否']},
    ]

    def get(self, task_type, task_id):
        """ 聚类校对页面"""

        def c2int(c):
            return int(float(c) * 1000)

        def get_user_filter():
            # 异文
            un_equal = self.get_query_argument('diff', 0)
            if un_equal == 'true':
                cond['diff'] = True
            # 是否不必校对
            un_required = self.get_query_argument('un_required', 0)
            if un_required == 'true':
                cond['un_required'] = True
            # 按置信度过滤
            cc = self.get_query_argument('cc', 0)
            if cc:
                m1 = re.search(r'^([><]=?)(0|1|[01]\.\d+)$', cc)
                m2 = re.search(r'^(0|1|[01]\.\d+),(0|1|[01]\.\d+)$', cc)
                if m1:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m1.group(1))
                    cond.update({'cc': {op: c2int(m1.group(2))} if op else cc})
                elif m2:
                    cond.update({'cc': {'$gte': c2int(m2.group(1)), '$lte': c2int(m2.group(2))}})
            # 按修改过滤
            update = self.get_query_argument('update', 0)
            if update == 'my':
                cond['txt_logs.user_id'] = self.user_id
            elif update == 'all':
                cond['txt_logs'] = {'$nin': [None, []]}
            # 是否已提交
            submitted = self.get_query_argument('submitted', 0)
            if submitted == 'true':
                cond['tasks.' + task_type] = self.task['_id']
            elif submitted == 'false':
                cond['tasks.' + task_type] = {'$ne': self.task['_id']}
            # 文字类型
            txt_type = self.get_query_argument('txt_type', '')
            if txt_type:
                cond['txt_type'] = txt_type

        try:
            # 1.根据任务参数，设置字数据的过滤条件
            params = self.task['params']
            ocr_txts = [c['ocr_txt'] for c in params]
            user_level = self.get_user_txt_level(self, task_type)
            cond = {'source': params[0]['source'], 'ocr_txt': {'$in': ocr_txts} if len(ocr_txts) > 1 else ocr_txts[0],
                    'txt_level': {'$lte': user_level}, 'un_required': None}
            # 统计任务相关字种
            counts = list(self.db.char.aggregate([
                {'$match': cond}, {'$group': {'_id': '$txt', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            txts = [c['_id'] for c in counts]
            v_txts = [int(t[1:]) for t in txts if t[0] == 'Y']
            if v_txts:
                v_txts = list(self.db.variant.find({'uid': {'$in': v_txts}}, {'uid': 1, 'img_name': 1}))
                v_txts = {'Y%s' % t['uid']: t['img_name'] for t in v_txts}
            # 设置当前字种及相关的异体字
            cur_txt, variants = self.get_query_argument('txt', ''), []
            cur_txt = cur_txt if cur_txt and cur_txt in txts else ''
            if cur_txt:
                cond.update({'txt': cur_txt})
                variants = list(self.db.variant.find({'$or': [{'txt': cur_txt}, {'normal_txt': cur_txt}]}))
            # 设置用户过滤条件
            get_user_filter()
            # 2.查找单字数据
            self.page_size = int(json_util.loads(self.get_secure_cookie('cluster_page_size') or '50'))
            docs, pager, q, order = Char.find_by_page(self, cond, default_order='cc')
            chars = {d['name']: d for d in docs}
            # 设置列图hash值
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['img_url'] = self.get_web_img(column_name, 'column')
            char_count = self.task.get('char_count')
            show_char_info = json_util.loads(self.get_secure_cookie('cluster_char_info') or '0') or '是'
            self.render(
                'char_cluster.html', docs=docs, pager=pager, q=q, order=order, chars=chars, ocr_txts=ocr_txts,
                txts=txts, v_txts=v_txts, cur_txt=cur_txt, variants=variants, char_count=char_count,
                show_char_info=show_char_info, Char=Char
            )

        except Exception as error:
            return self.send_db_error(error)
