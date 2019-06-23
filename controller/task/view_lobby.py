#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅
@time: 2018/12/26
"""
import random
from functools import cmp_to_key
from controller.task.base import TaskHandler


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    def get(self, task_type):
        """ 任务大厅 """
        try:
            tasks, total_count = self.get_lobby_tasks_by_type(self, task_type)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        select_lobby_text_proof=self.select_lobby_text_proof)
        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def get_lobby_tasks_by_type(self, task_type, page_size=0):
        """按优先级排序后随机获取任务大厅/任务列表"""

        def get_priority(page):
            t = self.select_lobby_text_proof(self, page) if task_type == 'text_proof' else task_type
            priority = self.prop(page, 'tasks.%s.priority' % t) or 0
            return priority

        if task_type not in self.all_types():
            return [], 0
        if task_type == 'text_proof':
            condition = {'$or': [{'tasks.text_proof_%s.status' % i: self.STATUS_OPENED} for i in [1, 2, 3]]}
            condition.update(
                {'tasks.text_proof_%s.picked_by' % i: {'$ne': self.current_user['_id']} for i in [1, 2, 3]})
        else:
            condition = {'tasks.%s.status' % task_type: self.STATUS_OPENED}
        total_count = self.db.page.count_documents(condition)
        pages = list(self.db.page.find(condition, self.simple_fileds()).limit(self.MAX_RECORDS))
        random.shuffle(pages)
        pages.sort(key=cmp_to_key(lambda a, b: get_priority(a) - get_priority(b)))
        page_size = page_size or self.config['pager']['page_size']
        return pages[:page_size], total_count

    @staticmethod
    def select_lobby_text_proof(self, page):
        """从一个page中，选择已发布且优先级最高的文字校对任务"""
        text_proof, priority = '', -1
        for i in range(1, 4):
            s = self.prop(page, 'tasks.text_proof_%s.status' % i)
            p = self.prop(page, 'tasks.text_proof_%s.priority' % i) or 0
            if s == self.STATUS_OPENED and p > priority:
                text_proof, priority = 'text_proof_%s' % i, p
        return text_proof