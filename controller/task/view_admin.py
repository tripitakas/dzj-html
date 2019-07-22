#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
from datetime import datetime
from controller.task.base import TaskHandler


class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

    # 默认前置任务，发布任务时供管理员参考
    default_pre_tasks = {
        'block_cut_review': ['block_cut_proof'],
        'column_cut_review': ['column_cut_proof'],
        'char_cut_review': ['char_cut_proof'],
        'text_review': ['text_proof_1', 'text_proof_2', 'text_proof_3'],
    }

    def get(self, task_type):
        """ 任务管理 """
        try:
            q = self.get_query_argument('q', '').upper()
            status = self.get_query_argument('status', '')
            order = self.get_query_argument('order', '')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_tasks_by_type(
                task_type, type_status=status, order=order, name=q, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('task_admin.html', task_type=task_type, tasks=tasks, pager=pager, order=order,
                        default_pre_tasks=self.default_pre_tasks)
        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskCutStatusHandler(TaskHandler):
    URL = '/task/admin/cut/status'

    def get(self):
        """ 切分任务状态 """

        try:
            status = self.get_query_argument('status', '')
            task_type = self.get_query_argument('type', '')
            q = self.get_query_argument('q', '').upper()
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_tasks_by_type(
                task_type=task_type, type_status=status, name=q, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('task_cut_status.html', tasks=tasks, pager=pager)
        except Exception as e:
            self.send_db_error(e, render=True)


class TaskTextStatusHandler(TaskHandler):
    URL = '/task/admin/text/status'

    def get(self):
        """ 文字任务状态 """

        try:
            status = self.get_query_argument('status', '')
            task_type = self.get_query_argument('type', '')
            q = self.get_query_argument('q', '').upper()
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_tasks_by_type(
                task_type=task_type, type_status=status, name=q, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('task_text_status.html', tasks=tasks, pager=pager)
        except Exception as e:
            self.send_db_error(e, render=True)


class TaskInfoHandler(TaskHandler):
    URL = '/task/info/@page_name'

    def get(self, page_name):
        """ 任务详情 """

        def format_value(key, value):
            """ 格式化任务信息"""
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M')
            elif key == 'status':
                value = self.status_names.get(value)
            elif key == 'pre_tasks':
                value = ' / '.join([self.task_types.get(t) for t in value])
            elif key == 'priority':
                value = self.prior_names.get(int(value))

            return value

        try:
            page = self.db.page.find_one({'name': page_name}, self.simple_fileds())
            field_names = {
                'status': '状态', 'pre_tasks': '前置任务', 'priority': '优先级',
                'publish_by': '发布人', 'publish_time': '发布时间',
                'picked_by': '领取人', 'picked_time': '领取时间',
                'updated_time': '更新时间', 'finished_time': '完成时间',
                'returned_reason': '退回理由',
            }
            self.render('task_info.html', page=page, field_names=field_names, format_value=format_value)

        except Exception as e:
            self.send_db_error(e, render=True)
