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
            self.render('my_task.html', task_type=task_type, tasks=tasks, pager=pager, order=order,
                        select_my_text_proof=self.select_my_text_proof)
        except Exception as e:
            return self.send_db_error(e, render=True)

    def get_my_tasks_by_type(self, task_type, name=None, order=None, page_size=0, page_no=1):
        """获取我的任务/任务列表"""
        if task_type not in self.task_types.keys() and task_type != 'text_proof':
            return [], 0

        if task_type == 'text_proof':
            condition = {
                '$or': [{
                    'tasks.text_proof_%s.picked_user_id' % i: self.current_user['_id'],
                    'tasks.text_proof_%s.status' % i: {"$in": [self.STATUS_PICKED, self.STATUS_FINISHED]},
                } for i in [1, 2, 3]]
            }
        else:
            condition = {
                'tasks.%s.picked_user_id' % task_type: self.current_user['_id'],
                'tasks.%s.status' % task_type: {"$in": [self.STATUS_PICKED, self.STATUS_FINISHED]},
            }

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

    def select_my_text_proof(self, page):
        """从一个page中，选择我的文字校对任务"""
        for i in range(1, 4):
            if self.prop(page, 'tasks.text_proof_%s.picked_user_id' % i) == self.current_user['_id']:
                return 'text_proof_%s' % i
