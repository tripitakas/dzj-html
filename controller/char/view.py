#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from .char import Char
from .base import CharHandler
from controller import helper as h
from controller import errors as e
from controller.page.base import PageHandler


class CharListHandler(CharHandler):
    URL = '/char/list'

    page_title = '字数据管理'
    table_fields = [
        {'id': 'has_img', 'name': '字图'},
        {'id': 'source', 'name': '分类'},
        {'id': 'page_name', 'name': '页编码'},
        {'id': 'cid', 'name': 'cid'},
        {'id': 'name', 'name': '字编码'},
        {'id': 'char_id', 'name': '字序'},
        {'id': 'uid', 'name': '字序id'},
        {'id': 'data_level', 'name': '数据等级'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'column', 'name': '所属列'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'txt', 'name': '原字'},
        {'id': 'nor_txt', 'name': '正字'},
        {'id': 'ocr_txt', 'name': '字框OCR'},
        {'id': 'ocr_col', 'name': '列框OCR'},
        {'id': 'cmp_txt', 'name': '比对文字'},
        {'id': 'alternatives', 'name': 'OCR候选'},
        {'id': 'diff', 'name': '是否不匹配'},
        {'id': 'txt_level', 'name': '文本等级'},
        {'id': 'txt_logs', 'name': '文本校对记录'},
        {'id': 'tasks', 'name': '校对任务'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/api/char/delete'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-gen-img', 'label': '生成字图'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'source', 'label': '按分类'},
            {'operation': 'txt', 'label': '按原字'},
            {'operation': 'ocr_txt', 'label': '按OCR'},
            {'operation': 'nor_txt', 'label': '按正字'},
        ]},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': name} for k, name in CharHandler.task_names('char', True).items()
        ]},
    ]
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/api/char/delete'},
    ]
    hide_fields = ['page_name', 'cid', 'uid', 'data_level', 'txt_logs', 'sc', 'pos', 'column', 'proof_count']
    info_fields = ['has_img', 'source', 'txt', 'nor_txt', 'txt_type', 'remark']
    update_fields = [
        {'id': 'txt_type', 'name': '类型', 'input_type': 'radio', 'options': Char.txt_types},
        {'id': 'source', 'name': '分类'},
        {'id': 'txt', 'name': '原字'},
        {'id': 'nor_txt', 'name': '正字'},
        {'id': 'remark', 'name': '备注'},
    ]

    yes_no = {True: '是', False: '否'}

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""

        def log2str(log):
            val = '|'.join(log[f] for f in ['txt', 'nor_txt', 'txt_type', 'remark', 'user_name'] if log.get(f))
            if log.get('updated_time'):
                val = val + '|' + h.get_date_time('%Y-%m-%d %H:%M', log.get('updated_time'))
            return val

        if key == 'pos' and value:
            return '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key == 'txt_type' and value:
            return self.txt_types.get(value, value)
        if key == 'diff':
            return self.yes_no.get(value) or ''
        if key in ['cc', 'sc'] and value:
            return value / 1000
        if key == 'txt_logs' and value:
            return '<br/>'.join([log2str(log) for log in value])
        if key == 'has_img' and value not in [None, False]:
            return r'<img class="char-img" src="%s"/>' % self.get_char_img(doc)
        return h.format_value(value, key, doc)

    def get(self):
        """ 字数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = Char.get_char_search_condition(self.request.query)
            docs, pager, q, order = Char.find_by_page(self, condition)
            self.render('char_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        txt_types=self.txt_types, yes_no=self.yes_no, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CharViewHandler(CharHandler, Char):
    URL = '/char/@char_name'

    def format_value(self, value, key=None, doc=None):
        """ 格式化task表的字段输出"""
        if key in ['cc', 'sc'] and value:
            return value / 1000
        if key in ['pos', 'column'] and value:
            return ', '.join(['%s:%s' % (k, v) for k, v in value.items()])
        if key == 'txt_type':
            return Char.txt_types.get(value) or value
        return h.format_value(value, key, doc)

    def get(self, char_name):
        """ 查看Char页面"""
        try:
            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到数据%s' % char_name)
            projection = {'name': 1, 'chars.$': 1, 'width': 1, 'height': 1, 'tasks': 1}
            page = self.db.page.find_one({'name': char['page_name'], 'chars.cid': char['cid']}, projection)
            if page and page['chars'][0].get('box_logs'):
                char['box_logs'] = page['chars'][0]['box_logs']
            if page and page['chars'][0].get('box_level'):
                char['box_level'] = page['chars'][0]['box_level']
            base_fields = ['name', 'page_name', 'char_id', 'source', 'cc', 'sc', 'pos', 'column',
                           'txt', 'nor_txt', 'txt_type', 'txt_level', 'box_level', 'remark']
            img_url = self.get_web_img(page['name'], 'page')
            txt_auth = self.check_txt_level_and_point(self, char, None, False) is True
            box_auth = PageHandler.check_box_level_and_point(self, char, page, None, False) is True
            chars = {char['name']: char}
            self.render('char_view.html', char=char, page=page, base_fields=base_fields, img_url=img_url,
                        txt_auth=txt_auth, box_auth=box_auth, chars=chars, Char=Char)

        except Exception as error:
            return self.send_db_error(error)


class CharStatHandler(CharHandler):
    URL = '/char/statistic'

    def get(self):
        """ 统计字数据"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            kind = self.get_query_argument('kind', '')
            if kind not in ['source', 'txt', 'ocr_txt', 'nor_txt']:
                return self.send_error_response(e.statistic_type_error, message='只能按分类、正字、原字和OCR文字统计')
            aggregates = [{'$group': {'_id': '$' + kind, 'count': {'$sum': 1}}}]
            docs, pager, q, order = Char.aggregate_by_page(self, condition, aggregates, default_order='-count')
            self.render('char_statistic.html', docs=docs, pager=pager, q=q, order=order, kind=kind, Char=Char)

        except Exception as error:
            return self.send_db_error(error)


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
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'bat-assign', 'label': '批量指派', 'data-target': 'assignModal'},
        {'operation': 'bat-batch', 'label': '更新批次'},
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
    hide_fields = ['_id', 'params', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

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


class CharBrowseHandler(CharHandler):
    URL = '/char/browse'

    page_size = 50

    def get(self):
        """ 浏览字图"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            docs, pager, q, order = Char.find_by_page(self, condition)
            chars = {str(d['name']): d for d in docs}
            column_url = ''
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order, column_url=column_url,
                        chars=chars)

        except Exception as error:
            return self.send_db_error(error)


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

        try:
            # 1.根据任务参数，设置字数据的过滤条件
            params = self.task['params']
            ocr_txts = [c['ocr_txt'] for c in params]
            user_level = self.get_user_txt_level(self, task_type)
            cond = {'source': params[0]['source'], 'ocr_txt': {'$in': ocr_txts}, 'txt_level': {'$lte': user_level}}
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
            cur_txt, variants = self.get_query_argument('txt', 0), []
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
            column_url = ''
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['hash'] = h.md5_encode(column_name, self.get_config('web_img.salt'))
                if not column_url:
                    column_url = self.get_web_img(column_name, 'column')
            char_count = self.task.get('char_count')
            show_char_info = json_util.loads(self.get_secure_cookie('cluster_char_info') or '0') or '是'
            self.render(
                'char_cluster.html', docs=docs, pager=pager, q=q, order=order, chars=chars, ocr_txts=ocr_txts,
                txts=txts, v_txts=v_txts, cur_txt=cur_txt, variants=variants, char_count=char_count,
                column_url=column_url, show_char_info=show_char_info, Char=Char
            )

        except Exception as error:
            return self.send_db_error(error)
