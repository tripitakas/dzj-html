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
            q = self.get_query_argument('q', '').upper()
            order = self.get_query_argument('order', '')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_my_tasks_by_type(
               task_type=task_type, name=q, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            task_name = self.task_types[task_type]['name']
            self.render('my_task.html', tasks=tasks, task_type=task_type, task_name=task_name, pager=pager, order=order)
        except Exception as e:
            self.send_db_error(e, render=True)
