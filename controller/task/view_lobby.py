#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅
@time: 2018/12/26
"""
from controller.task.base import TaskHandler


class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    def get(self, task_type):
        """ 任务大厅 """
        try:
            tasks, total_count = self.get_lobby_tasks_by_type(task_type)
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, total_count=total_count,
                        select_lobby_text_proof=self.select_lobby_text_proof)
        except Exception as e:
            self.send_db_error(e, render=True)
