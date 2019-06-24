#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
from controller.task.base import TaskHandler


class TaskAdminBaseHandler(TaskHandler):
    def get_tasks_by_type(self, task_type, type_status=None, name=None, order=None, page_size=0, page_no=1):
        """获取任务管理/任务列表"""
        if task_type and task_type not in self.task_types.keys():
            return [], 0

        condition = dict()
        if task_type and type_status:
            condition['tasks.%s.status' % task_type] = type_status
        if name:
            condition['name'] = {'$regex': '.*%s.*' % name}

        query = self.db.page.find(condition, self.simple_fileds())
        total_count = query.count()

        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort("%s.%s" % (task_type, order), asc)

        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count


class TaskAdminHandler(TaskAdminBaseHandler):
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


class TaskCutStatusHandler(TaskAdminBaseHandler):
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


class TaskTextStatusHandler(TaskAdminBaseHandler):
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
