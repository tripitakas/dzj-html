#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
from controller.task.base import TaskHandler


class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

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
            self.render('task_admin.html', task_type=task_type, tasks=tasks, pager=pager, order=order)
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
