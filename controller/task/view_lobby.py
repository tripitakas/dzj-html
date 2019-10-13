#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅
@time: 2018/12/26
"""
import random
from controller.task.base import TaskHandler


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    def get_lobby_tasks_by_type(self, task_type, page_size=None):
        """按优先级排序后随机获取任务大厅/任务列表"""

        def get_skip_no():
            condition.update({'priority': 3})
            n3 = self.db.task.count_documents(condition)
            condition.update({'priority': 2})
            n2 = self.db.task.count_documents(condition)
            del condition['priority']
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        def de_duplicate():
            """根据id_value去重"""
            _tasks, _id_values = [], []
            for task in tasks:
                if task.get('id_value') not in _id_values:
                    _tasks.append(task)
                    _id_values.append(task.get(id_name))
            return _tasks[:page_size]

        if task_type not in self.all_task_types():
            return [], 0

        task_meta = self.all_task_types().get(task_type)
        collection, id_name = task_meta['data']['collection'], task_meta['data']['id']
        page_size = page_size or self.config['pager']['page_size']
        if task_meta.get('groups'):
            condition = {'task_type': {'$regex': '.*%s.*' % task_type}, 'status': self.STATUS_OPENED}
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition = {'task_type': task_type, 'status': self.STATUS_OPENED}
            total_count = self.db.task.count_documents(condition)
            skip_no = get_skip_no()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            tasks, total_count = self.get_lobby_tasks_by_type(task_type)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as e:
            self.send_db_error(e, render=True)
