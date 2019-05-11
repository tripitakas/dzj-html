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
            tasks = self.get_tasks_info_by_type(task_type)
            task_name = self.task_types[task_type]['name']
            has_sub_tasks = 'sub_task_types' in self.task_types[task_type]

            self.render('task_admin.html',
                        tasks=tasks, task_type=task_type, task_name=task_name, has_sub_tasks=has_sub_tasks,
                        task_types=self.task_types, task_statuses=self.task_statuses)
        except Exception as e:
            self.send_db_error(e, render=True)


class TaskCutStatusHandler(TaskHandler):
    URL = '/task/admin/cut/status'

    def get(self):
        """ 切分任务状态 """

        try:
            tasks = self.get_tasks_info()
            self.render('task_cut_status.html', tasks=tasks, task_statuses=self.task_statuses,
                        task_names=self.cut_task_names)
        except Exception as e:
            self.send_db_error(e, render=True)


class TaskTextStatusHandler(TaskHandler):
    URL = '/task/admin/text/status'

    def get(self):
        """ 文字任务状态 """

        try:
            tasks = self.get_tasks_info()
            self.render('task_text_status.html', tasks=tasks, task_statuses=self.task_statuses,
                        task_names=self.text_task_names)
        except Exception as e:
            self.send_db_error(e, render=True)
