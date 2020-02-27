#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import re
from bson import json_util
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class DocTaskAdminHandler(TaskHandler):
    URL = '/task/admin/(page)'

    page_title = '页任务管理'
    search_tips = '请搜索页编码、批次号或备注'
    search_fields = ['doc_id', 'batch', 'remark']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'bat-assign', 'label': '批量指派', 'data-target': 'assignModal'},
        {'operation': 'bat-update', 'label': '更新批次', 'data-target': 'batchModal'},
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
        {'action': 'btn-history', 'label': '历程'},
        {'action': 'btn-delete', 'label': '删除'},
        {'action': 'btn-republish', 'label': '重新发布', 'disabled': lambda d: d['status'] not in ['picked', 'failed']},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

    def get(self, collection):
        """ 任务管理-页任务管理"""
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['table_fields'] = [
                {'id': '_id', 'name': '主键'},
                {'id': 'doc_id', 'name': '页编码'},
                {'id': 'batch', 'name': '批次号'},
                {'id': 'task_type', 'name': '类型', 'filter': self.get_task_types(collection)},
                {'id': 'status', 'name': '状态', 'filter': self.task_statuses},
                {'id': 'priority', 'name': '优先级', 'filter': self.priorities},
                {'id': 'steps', 'name': '步骤'},
                {'id': 'pre_tasks', 'name': '前置任务'},
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
            condition, params = self.get_task_search_condition(self.request.query, collection)
            p = {f: 0 for f in ['input', 'result']}
            docs, pager, q, order = self.find_by_page(self, condition, self.search_fields, '-_id', p)
            self.render(
                'task_admin_doc.html', docs=docs, pager=pager, order=order, q=q, params=params,
                collection=collection, **kwargs,
            )
        except Exception as error:
            return self.send_db_error(error)


class ImageTaskAdminHandler(TaskHandler):
    URL = '/task/admin/image'

    page_title = '页图片任务管理'
    search_tips = '请搜索批次、网盘名称或导入文件夹'
    search_fields = ['batch', 'input.pan_name', 'input.import_dir']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'title': '/task/delete'},
        {'operation': 'btn-publish', 'label': '发布任务', 'data-target': 'publishModal'},
    ]
    img_operations = []
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-remove', 'label': '删除', 'title': '/task/delete'},
        {'action': 'btn-republish', 'label': '重新发布'},
    ]
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'batch', 'name': '批次'},
        {'id': 'input-pan_name', 'name': '网盘名称'},
        {'id': 'input-import_dir', 'name': '导入文件夹'},
        {'id': 'input-layout', 'name': '版面结构'},
        {'id': 'input-redo', 'name': '是否覆盖已有图片'},
        {'id': 'status', 'name': '状态'},
        {'id': 'priority', 'name': '优先级', 'filter': TaskHandler.priorities},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

    def get(self):
        """ 任务管理/页图片任务 """
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            # 检索条件
            condition = dict(task_type='import_image')
            priority = self.get_query_argument('priority', '')
            if priority:
                condition.update({'priority': int(priority)})
            # 查询数据
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-publish_time')
            self.render(
                'task_admin_image.html', docs=docs, pager=pager, order=order, q=q,
                pan_name=self.prop(self.config, 'pan.name'), **kwargs,
            )

        except Exception as error:
            return self.send_db_error(error)


class DocTaskStatisticHandler(TaskHandler):
    URL = '/task/(page)/statistic'

    def get(self, collection):
        """ 根据用户、任务类型或任务状态统计页任务"""
        try:
            condition = self.get_task_search_condition(self.request.query, collection)[0]
            kind = self.get_query_argument('kind', '')
            if kind not in ['picked_user_id', 'task_type', 'status']:
                return self.send_error_response(e.statistic_type_error, message='只能按用户、任务类型或任务状态统计')

            counts = list(self.db.task.aggregate([
                {'$match': condition},
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

            self.render('task_statistic.html', counts=counts, kind=kind, label=label, trans=trans)

        except Exception as error:
            return self.send_db_error(error)


class LobbyTaskHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    def get(self, task_type):
        """ 任务大厅"""
        try:
            q = self.get_query_argument('q', '')
            tasks, total_count = self.find_lobby(task_type, q=q)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as error:
            return self.send_db_error(error)


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    search_tips = '请搜索页编码'
    search_fields = ['doc_id']
    operations = []
    img_operations = []
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续', 'disabled': lambda d: d['status'] == 'finished'},
        {'action': 'my-task-update', 'label': '更新', 'disabled': lambda d: d['status'] == 'picked'},
    ]
    table_fields = [
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'status', 'name': '状态'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['task_type']
    update_fields = []

    def get(self, task_type):
        """ 我的任务"""
        try:
            condition = {
                'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type,
                'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]},
                'picked_user_id': self.user_id
            }
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            kwargs = self.get_template_kwargs()
            self.render('task_my.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class TaskDetailHandler(TaskHandler):
    URL = '/task/detail/@task_id'

    def get(self, task_id):
        """ 页面任务详情"""
        try:
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')
            self.render('task_detail.html', task=task)

        except Exception as error:
            return self.send_db_error(error)


class PageTaskResumeHandler(TaskHandler):
    URL = '/task/resume/page/@page_name'

    order = [
        'upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof_1',
        'text_proof_2', 'text_proof_3', 'text_review', 'text_hard'
    ]
    display_fields = [
        'doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
        'updated_time', 'finished_time', 'publish_by', 'publish_time',
        'picked_by', 'picked_time', 'message'
    ]

    def get(self, page_name):
        """ 页面任务简历"""
        from functools import cmp_to_key
        try:
            page = self.db.page.find_one({'name': page_name}) or dict(name=page_name)
            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            tasks.sort(key=cmp_to_key(lambda a, b: self.order.index(a['task_type']) - self.order.index(b['task_type'])))
            self.render('task_resume.html', page=page, tasks=tasks, display_fields=self.display_fields)

        except Exception as error:
            return self.send_db_error(error)


class TaskSampleHandler(TaskHandler):
    URL = '/task/sample/@task_type'

    def get(self, task_type):
        """ 练习任务"""
        try:
            condition = [{'$match': {'task_type': task_type, 'is_sample': True}}, {'$sample': {'size': 1}}]
            tasks = list(self.db.task.aggregate(condition))
            if not tasks:
                message = '没有找到%s的练习任务' % self.get_task_name(task_type)
                return self.send_error_response(e.no_object, message=message)
            else:
                return self.redirect('/task/%s/%s' % (task_type, tasks[0]['_id']))

        except Exception as error:
            return self.send_db_error(error)
