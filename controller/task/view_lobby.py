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
            n3 = self.db[table].count_documents(condition)
            condition.update({'priority': 2})
            n2 = self.db[table].count_documents(condition)
            del condition['priority']
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        if task_type not in self.task_types:
            return [], 0

        task_meta = self.task_types[task_type]
        table, table_id = task_meta['data']['table'], task_meta['data']['id']
        page_size = page_size or self.config['pager']['page_size']
        if task_meta.get('groups'):
            condition = {'task_type': {'$regex': '.*%s.*' % task_type}, 'status': self.STATUS_OPENED}
            total_count = self.db[table].count_documents(condition)
            skip_no = get_skip_no()
            documents = list(self.db[table].find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            # 根据table_id去重
            _documents, _doc_ids = [], []
            for document in documents:
                if document.get(table_id) not in _doc_ids:
                    _documents.append(document)
                    _doc_ids.append(document.get(table_id))
            documents = _documents[:page_size]
        else:
            condition = {'task_type': task_type, 'status': self.STATUS_OPENED}
            total_count = self.db[table].count_documents(condition)
            skip_no = get_skip_no()
            documents = list(self.db[table].find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return documents, total_count

    def get(self, task_type):
        """ 任务大厅 """
        try:
            tasks, total_count = self.get_lobby_tasks_by_type(task_type)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count)
        except Exception as e:
            self.send_db_error(e, render=True)
