#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 我的任务
@time: 2018/12/26
"""
from .base import TaskHandler


class MyTaskHandler(TaskHandler):
    URL = '/task/my/@task_type'

    def get_my_tasks_by_type(self, task_type, q=None, order=None, page_size=0, page_no=1):
        """获取我的任务/任务列表"""
        if task_type not in self.all_task_types():
            return [], 0

        task_meta = self.all_task_types()[task_type]
        condition = {
            'task_type': {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type,
            'picked_user_id': self.current_user['_id'],
            'status': {"$in": [self.STATUS_PICKED, self.STATUS_FINISHED]}
        }
        if q:
            condition.update({'id_value': {'$regex': '.*%s.*' % q}})
        query = self.db[task_meta['data']['collection']].find(condition)
        total_count = self.db.page.count_documents(condition)
        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(order, asc)
        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count

    def get(self, task_type):
        """ 我的任务 """
        try:
            q = self.get_query_argument('q', '').upper()
            order = self.get_query_argument('order', '-picked_time')
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            tasks, total_count = self.get_my_tasks_by_type(
                task_type=task_type, q=q, order=order, page_size=page_size, page_no=cur_page
            )
            pager = dict(cur_page=cur_page, item_count=total_count, page_size=page_size)
            self.render('my_task.html', task_type=task_type, tasks=tasks, pager=pager, order=order)
        except Exception as e:
            return self.send_db_error(e, render=True)
