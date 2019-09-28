#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理
@time: 2018/12/26
"""
from datetime import datetime
from controller.task.base import TaskHandler
from controller.task.view_cut import CutHandler


class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

    # 默认前置任务
    default_pre_tasks = {
        'cut_review': ['cut_proof'],
        'text_review': ['text_proof_1', 'text_proof_2', 'text_proof_3'],
    }

    # 默认任务步骤
    default_task_steps = {
        'cut_proof': CutHandler.steps,
        'cut_review': CutHandler.steps,
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
                        default_pre_tasks=self.default_pre_tasks.get(task_type, {}),
                        default_task_steps=self.default_task_steps.get(task_type, {}))
        except Exception as e:
            return self.send_db_error(e, render=True)


class TaskStatusHandler(TaskHandler):
    URL = '/task/admin/task_status'

    def get(self):
        """ 任务状态 """

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
            self.render('task_status.html', tasks=tasks, pager=pager)
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
                value = '/'.join([self.task_types.get(t) for t in value])
            elif key == 'steps':
                value = '/'.join([step_names.get(t, '') for t in value.get('todo', [])])
            elif key == 'priority':
                value = self.prior_names.get(int(value))
            return value

        step_names = dict()
        for steps in TaskAdminHandler.default_task_steps.values():
            step_names.update({k: v.get('name', '') for k, v in steps.items()})
        try:
            page = self.db.page.find_one({'name': page_name}, self.simple_fields())
            field_names = {
                'status': '状态', 'pre_tasks': '前置任务', 'steps': '步骤', 'priority': '优先级',
                'publish_by': '发布人', 'publish_time': '发布时间',
                'picked_by': '领取人', 'picked_time': '领取时间',
                'updated_time': '更新时间', 'finished_time': '完成时间',
                'returned_reason': '退回理由',
            }
            self.render('task_info.html', page=page, field_names=field_names, format_value=format_value)

        except Exception as e:
            self.send_db_error(e, render=True)
