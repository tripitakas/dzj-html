#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
import random
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

    def is_mod_enabled(self, mod):
        disabled_mods = self.prop(self.config, 'modules.disabled_mods')
        return not disabled_mods or mod not in disabled_mods

    def get(self, task_type):
        """ 任务管理/任务列表 """

        def statistic():
            doc_count = int(pager['doc_count'])
            q = self.get_query_argument('q', '')
            if q:
                condition['$or'] = [{k: {'$regex': q, '$options': '$i'}} for k in search_fields]
            if 'status' in condition:
                return {condition['status']: dict(count=doc_count, ratio=1)}
            result = dict()
            for status, name in self.task_statuses.items():
                condition.update({'status': status})
                count = self.db.task.count_documents(condition)
                if count:
                    result[status] = dict(count=count, ratio='%.2f' % (count / doc_count))
            return result

        try:
            condition = dict()
            if self.get_query_argument('task_type', ''):
                condition.update({'task_type': self.get_query_argument('task_type', '')})
            elif self.is_group(task_type):
                condition.update({'task_type': {'$regex': task_type}})
            else:
                condition.update({'task_type': task_type})
            if self.get_query_argument('status', ''):
                condition.update({'status': self.get_query_argument('status', '')})
            search_tip, search_fields, template = self.search_tip, self.search_fields, 'task_admin.html'
            if task_type == 'import_image':
                template = 'task_admin_import.html'
                search_tip = '请搜索网盘名称或导入文件夹'
                search_fields = ['input.pan_name', 'input.import_dir']
            tasks, pager, q, order = self.find_by_page(self, condition, search_fields)
            self.render(
                template, task_type=task_type, tasks=tasks, pager=pager, order=order, q=q, search_tip=search_tip,
                task_types=self.all_task_types(), is_mod_enabled=self.is_mod_enabled, statistic=statistic(),
                pan_name=self.prop(self.config, 'pan.name'), modal_fields=self.modal_fields,
                task_meta=self.get_task_meta(task_type),
            )
        except Exception as error:
            return self.send_db_error(error)


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    @staticmethod
    def get_lobby_tasks_by_type(self, task_type, page_size=None, q=None):
        """ 按优先级排序后随机获取任务大厅/任务列表"""

        def get_random_skip():
            condition.update({'priority': 3})
            n3 = self.db.task.count_documents(condition)
            condition.update({'priority': 2})
            n2 = self.db.task.count_documents(condition)
            condition.pop('priority', 0)
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        def de_duplicate():
            _tasks, _doc_ids = [], []
            for task in tasks:
                if task.get('doc_id') not in _doc_ids:
                    _tasks.append(task)
                    _doc_ids.append(task.get('doc_id'))
            return _tasks[:page_size]

        assert task_type in self.all_task_types()
        page_size = page_size or int(self.config['pager']['page_size'])
        condition = {'doc_id': {'$regex': q, '$options': '$i'}} if q else {}
        if self.is_group(task_type):
            condition.update({'task_type': {'$regex': task_type}, 'status': self.STATUS_OPENED})
            my_tasks = self.find_many(task_type, mine=True)
            if my_tasks:
                condition.update({'doc_id': {'$nin': [t['doc_id'] for t in my_tasks]}})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition.update({'task_type': task_type, 'status': self.STATUS_OPENED})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            q = self.get_query_argument('q', '')
            tasks, total_count = self.get_lobby_tasks_by_type(self, task_type, q=q)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as error:
            return self.send_db_error(error)


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    search_fields = ['doc_id']
    search_tip = '请搜索页编码'
    operations = []
    table_fields = [dict(id='doc_id', name='页编码'), dict(id='status', name='任务状态'),
                    dict(id='picked_time', name='领取时间'), dict(id='finished_time', name='完成时间')]
    actions = [
        {'action': 'my-task-do', 'label': '继续'},
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-update', 'label': '修改'},
    ]

    def get(self, task_type):
        """ 我的任务 """
        try:
            status = [self.STATUS_PICKED, self.STATUS_FINISHED]
            condition = {'status': {'$in': status}, 'picked_user_id': self.current_user['_id']}
            if task_type:
                condition.update({'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type})
            tasks, pager, q, order = self.find_by_page(self, condition)
            self.page_title = '我的任务-' + self.get_task_name(task_type)
            self.render('my_task.html', tasks=tasks, pager=pager, q=q, order=order, model=self)

        except Exception as error:
            return self.send_db_error(error)


class TaskPageInfoHandler(TaskHandler):
    URL = '/task/page/@page_name'

    def get(self, page_name):
        """ Page的任务详情 """
        from functools import cmp_to_key

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            tasks = list(self.db.task.find({'collection': 'page', 'doc_id': page_name}))
            order = ['upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof_1',
                     'text_proof_2', 'text_proof_3', 'text_review', 'text_hard']
            tasks.sort(key=cmp_to_key(lambda a, b: order.index(a['task_type']) - order.index(b['task_type'])))
            display_fields = ['doc_id', 'task_type', 'status', 'pre_tasks', 'steps', 'priority',
                              'updated_time', 'finished_time', 'publish_by', 'publish_time',
                              'picked_by', 'picked_time', 'message']
            self.render('task_page_info.html', page=page, tasks=tasks, format_value=self.format_value,
                        display_fields=display_fields)

        except Exception as error:
            return self.send_db_error(error)


class TaskInfoHandler(TaskHandler):
    URL = '/task/info/@task_id'

    def get(self, task_id):
        """ 任务详情 """
        try:
            # 检查参数
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')

            display_fields = ['doc_id', 'task_type', 'status', 'priority', 'pre_tasks', 'steps',
                              'publish_time', 'publish_by', 'picked_time', 'picked_by',
                              'updated_time', 'finished_time', 'message', ]
            self.render('task_info.html', task=task, display_fields=display_fields,
                        format_value=TaskPageInfoHandler.format_value)

        except Exception as error:
            return self.send_db_error(error)
