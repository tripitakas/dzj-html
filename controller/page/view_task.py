#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from datetime import datetime
from operator import itemgetter
from controller import errors as e
from controller.page.base import PageHandler
from controller.page.view import PageTxtHandler


class PageTaskListHandler(PageHandler):
    URL = '/page/task/list'

    page_title = '页任务管理'
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次号'},
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'task_type', 'name': '类型', 'filter': PageHandler.task_names('page', True, True)},
        {'id': 'num', 'name': '校次'},
        {'id': 'pre_tasks', 'name': '前置任务'},
        {'id': 'status', 'name': '状态', 'filter': PageHandler.task_statuses},
        {'id': 'priority', 'name': '优先级', 'filter': PageHandler.priorities},
        {'id': 'is_oriented', 'name': '是否定向', 'filter': PageHandler.yes_no},
        {'id': 'char_count', 'name': '单字数量'},
        {'id': 'added', 'name': '新增'},
        {'id': 'deleted', 'name': '删除'},
        {'id': 'changed', 'name': '修改'},
        {'id': 'total', 'name': '所有'},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
        {'id': 'used_time', 'name': '执行时间'},
        {'id': 'remark', 'name': '备注'},
    ]
    search_fields = ['doc_id', 'batch', 'remark']
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
            {'operation': 'bat-republish', 'label': '批量重做'},
            {'operation': 'bat-assign', 'label': '批量指派'},
            {'operation': 'btn-export', 'label': '导出页码'},
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-history', 'label': '历程'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'pre_tasks', 'publish_by', 'remark']
    update_fields = []

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs()
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:
            kwargs['actions'] = [{'action': 'btn-nav', 'label': '浏览'}]
            kwargs['operations'] = [{'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'}]
        return kwargs

    def get_task_search_condition(self, request_query, collection=None):
        condition, params = super().get_task_search_condition(request_query, collection)
        readonly = '任务管理员' not in self.current_user['roles']
        if readonly:
            condition['task_type'] = {'$in': ['cut_proof', 'cut_review']}
        return condition, params

    def get(self):
        """ 任务管理-页任务管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            cd, params = self.get_task_search_condition(self.request.query, 'page')
            docs, pager, q, order = self.find_by_page(self, cd, self.search_fields, '-_id', {'params': 0, 'result': 0})
            self.render('page_task_list.html', docs=docs, pager=pager, order=order, q=q, params=params,
                        format_value=self.format_value,
                        **kwargs)
        except Exception as error:
            return self.send_db_error(error)


class PageTaskStatisticHandler(PageHandler):
    URL = '/page/task/statistic'

    def get(self):
        """ 根据用户、任务类型或任务状态统计页任务"""
        try:
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status', 'batch']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、批次、任务类型或任务状态统计')

            counts = list(self.db.task.aggregate([
                {'$match': self.get_task_search_condition(self.request.query, 'page')[0]},
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

            self.render('task_statistic.html', counts=counts, kind=kind, total=total, head=head, rows=rows,
                        collection='page', title='页任务统计')

        except Exception as error:
            return self.send_db_error(error)


class PageTaskDashBoardHandler(PageHandler):
    URL = '/page/task/dashboard'

    def get(self):
        """ 综合统计"""
        self.task_dashboard(self, 'page')

    @staticmethod
    def task_dashboard(self, collection):
        def get_cond(field):
            cnd = {}
            start and cnd.update({'$gt': start})
            end and cnd.update({'$lt': end})
            return {field: cnd} if cnd else {}

        def get_params(field):
            cnd = {}
            start and cnd.update({field.replace('_time', '_start'): start.strftime('%Y-%m-%d %H:%M:%S')})
            end and cnd.update({field.replace('_time', '_end'): end.strftime('%Y-%m-%d %H:%M:%S')})
            return cnd

        try:
            start = self.get_query_argument('start', 0)
            if start:
                start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            end = self.get_query_argument('end', 0)
            if end:
                end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
            task_types = [k for k, t in self.task_types.items() if self.prop(t, 'data.collection') == collection]
            # 本阶段发布
            this_publish = list(self.db.task.aggregate([
                {'$match': {**get_cond('publish_time'), 'collection': collection}},
                {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            this_publish = {t['_id']: t['count'] for t in this_publish}
            this_publish['all'] = sum([t for t in this_publish.values()])
            # 本阶段完成
            this_finish = list(self.db.task.aggregate([
                {'$match': {**get_cond('finished_time'), 'collection': collection}},
                {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            this_finish = {t['_id']: t['count'] for t in this_finish}
            this_finish['all'] = sum([t for t in this_finish.values()])
            # 本阶段退回
            this_return = list(self.db.task.aggregate([
                {'$match': {**get_cond('updated_time'), 'status': self.STATUS_RETURNED, 'collection': collection}},
                {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            this_return = {t['_id']: t['count'] for t in this_return}
            this_return['all'] = sum([t for t in this_return.values()])
            # 所有完成
            all_finish = {}
            if start or end:
                all_finish = list(self.db.task.aggregate([
                    {'$match': {'status': self.STATUS_FINISHED, 'collection': collection}},
                    {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}},
                ]))
                all_finish = {t['_id']: t['count'] for t in all_finish}
                all_finish['all'] = sum([t for t in all_finish.values()])
            # 所有进行中
            all_pick = list(self.db.task.aggregate([
                {'$match': {'status': self.STATUS_PICKED, 'collection': collection}},
                {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            all_pick = {t['_id']: t['count'] for t in all_pick}
            all_pick['all'] = sum([t for t in all_pick.values()])
            # 所有未完成
            all_publish = list(self.db.task.aggregate([
                {'$match': {'status': self.STATUS_PUBLISHED, 'collection': collection}},
                {'$group': {'_id': '$task_type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
            ]))
            all_publish = {t['_id']: t['count'] for t in all_publish}
            all_publish['all'] = sum([t for t in all_publish.values()])
            daily_finish, expected_finish = {}, {}
            days = (((end or self.now()) - start).days + 1) if start else 0
            if start:
                # 日均完成
                daily_finish = {t: round(this_finish.get(t, 0) / days, 1) for t in task_types}
                daily_finish['all'] = round(sum([t for t in daily_finish.values()]), 1)
                # 预计完成
                expected_finish = {t: round(all_publish.get(t, 0) / daily_finish.get(t), 1) for t in task_types
                                   if daily_finish.get(t)}

            dataset = {'本期限发布': this_publish, '本期限完成': this_finish, '本期限退回': this_return,
                       '所有已完成': all_finish, '所有进行中': all_pick, '所有未完成': all_publish,
                       '日均(%s日)完成' % days: daily_finish, '预计还需几天完成': expected_finish}
            dataset = {k: v for k, v in dataset.items() if v}
            column_sum = {t: sum([d.get(t, 0) for d in dataset.values()]) for t in task_types}
            task_types = [t for t, s in column_sum.items() if s]

            params = {'本期限发布': get_params('publish_time'), '本期限完成': get_params('finished_time'),
                      '本期限退回': {**get_params('updated_time'), 'status': self.STATUS_RETURNED},
                      '所有已完成': {'status': self.STATUS_FINISHED}, '所有进行中': {'status': self.STATUS_PICKED},
                      '所有未完成': {'status': self.STATUS_PUBLISHED}}

            self.render('task_dashboard.html', task_types=task_types, start=start, end=end, days=days, params=params,
                        dataset=dataset, collection=collection)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskResumeHandler(PageHandler):
    URL = '/page/task/resume/@page_name'

    order = [
        'upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof', 'text_review',
    ]
    display_fields = [
        'doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
        'updated_time', 'finished_time', 'publish_by', 'publish_time',
        'picked_by', 'picked_time', 'message'
    ]

    def get(self, page_name):
        """ 页任务简历"""
        from functools import cmp_to_key
        try:
            page = self.db.page.find_one({'name': page_name}) or dict(name=page_name)
            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            tasks.sort(key=cmp_to_key(lambda a, b: self.order.index(a['task_type']) - self.order.index(b['task_type'])))
            self.render('task_resume.html', page=page, tasks=tasks, display_fields=self.display_fields)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskCutHandler(PageHandler):
    URL = ['/task/(cut_proof|cut_review)/@task_id',
           '/task/do/(cut_proof|cut_review)/@task_id',
           '/task/nav/(cut_proof|cut_review)/@task_id',
           '/task/update/(cut_proof|cut_review)/@task_id',
           '/task/browse/(cut_proof|cut_review|ocr_box|ocr_text)/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对、审定页面"""
        try:
            page = self.db.page.find_one({'name': self.task['doc_id']})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % self.task['doc_id'])
            self.pack_boxes(page)
            page['img_url'] = self.get_page_img(page)

            tasks = list(self.db.task.find({'doc_id': page['name']}, {
                k: 1 for k in ['task_type', 'picked_by', 'picked_user_id']}))
            tasks = [t for t in tasks if t.get('picked_user_id') and t['picked_user_id'] != self.user_id]
            task_names = dict(cut_proof='校对', cut_review='审定')

            self.render('page_box.html', page=page, readonly=self.readonly, mode=self.mode,
                        task_type=task_type, tasks=tasks, task_names=task_names)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskTextHandler(PageHandler):
    URL = ['/task/(text_proof|text_review)/@task_id',
           '/task/do/(text_proof|text_review)/@task_id',
           '/task/nav/(text_proof|text_review)/@task_id',
           '/task/browse/(text_proof|text_review)/@task_id',
           '/task/update/(text_proof|text_review)/@task_id']

    def get(self, task_type, task_id):
        """ 文字校对、审定页面"""
        try:
            self.page_title = '文字审定' if task_type == 'text_review' else '文字校对'
            PageTxtHandler.page_txt(self, self.task['doc_id'])

        except Exception as error:
            return self.send_db_error(error)
