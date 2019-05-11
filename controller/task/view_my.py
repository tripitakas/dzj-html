#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 我的任务
@time: 2018/12/26
"""
from controller.task.base import TaskHandler


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    def get(self, task_type):
        """ 我的任务 """
        try:
            tasks = list(self.get_my_tasks_by_type(task_type))
            task_name = self.task_types[task_type]['name']
            has_sub_tasks = 'sub_task_types' in self.task_types[task_type]

            self.render('my_task.html',
                        tasks=tasks, task_type=task_type, task_name=task_name, has_sub_tasks=has_sub_tasks,
                        task_types=self.task_types, task_statuses=self.task_statuses)
        except Exception as e:
            self.send_db_error(e, render=True)
