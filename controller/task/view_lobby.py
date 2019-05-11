#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务大厅
@time: 2018/12/26
"""
from controller.task.base import TaskHandler


class TaskLobbyHandler(TaskHandler):
    """ 任务大厅基类 """

    def show_tasks(self, task_type):
        def pack(items):
            """设置任务的priority、pick_url、status等属性"""
            for t in items:
                if not self.task_types.get(task_type, {}).get('sub_task_types'):  # 一级任务
                    current_task = t.get(task_type, {})
                    t['priority'] = current_task.get('priority')
                    t['pick_url'] = '/task/pick/%s/%s' % (task_type, t['name'])
                    t['status'] = current_task.get('status')
                else:  # 二级任务
                    for k, sub_task in t.get(task_type, {}).items():
                        if sub_task.get('status') == self.STATUS_OPENED:
                            t['priority'] = sub_task.get('priority')
                            t['pick_url'] = '/task/pick/%s/%s' % (task_type, t['name'])
                            t['status'] = sub_task.get('status')
                            continue

        try:
            tasks = self.get_tasks(task_type, self.STATUS_OPENED)
            pack(tasks)
            task_name = self.task_types[task_type]['name']
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, task_name=task_name)
        except Exception as e:
            self.send_db_error(e, render=True)

    def get_tasks(self, task_type, task_status):
        return self.get_tasks_info_by_type(task_type, task_status, rand=True, sort=True)


class TextProofTaskLobbyHandler(TaskLobbyHandler):
    URL = '/task/lobby/text_proof'

    def get(self):
        """ 任务大厅-文字校对 """
        self.show_tasks('text_proof')

    def get_tasks(self, task_type, task_status):
        sub_types = self.task_types[task_type]['sub_task_types'].keys()
        not_me = {'%s.%s.user' % (task_type, t): {'$ne': self.current_user['_id']} for t in sub_types}
        tasks = self.get_tasks_info_by_type(
            task_type, task_status, rand=True, sort=True,
            set_conditions=lambda cond: cond.update(not_me)
        )
        return tasks


class TextReviewTaskLobbyHandler(TaskLobbyHandler):
    URL = '/task/lobby/text_review'

    def get(self):
        """ 任务大厅-文字审定 """
        self.show_tasks('text_review')


class TextHardTaskLobbyHandler(TaskLobbyHandler):
    URL = '/task/lobby/text_hard'

    def get(self):
        """ 任务大厅-难字处理 """
        self.show_tasks('text_hard')


class LobbyBlockCutProofHandler(TaskLobbyHandler):
    URL = '/task/lobby/block_cut_proof'

    def get(self):
        """ 任务大厅-栏切分校对 """
        self.show_tasks('block_cut_proof')


class LobbyColumnCutProofHandler(TaskLobbyHandler):
    URL = '/task/lobby/column_cut_proof'

    def get(self):
        """ 任务大厅-列切分校对 """
        self.show_tasks('column_cut_proof')


class LobbyCharCutProofHandler(TaskLobbyHandler):
    URL = '/task/lobby/char_cut_proof'

    def get(self):
        """ 任务大厅-字切分校对 """
        self.show_tasks('char_cut_proof')


class LobbyBlockCutReviewHandler(TaskLobbyHandler):
    URL = '/task/lobby/block_cut_review'

    def get(self):
        """ 任务大厅-栏切分审定 """
        self.show_tasks('block_cut_review')


class LobbyColumnCutReviewHandler(TaskLobbyHandler):
    URL = '/task/lobby/column_cut_review'

    def get(self):
        """ 任务大厅-列切分审定 """
        self.show_tasks('column_cut_review')


class LobbyCharCutReviewHandler(TaskLobbyHandler):
    URL = '/task/lobby/char_cut_review'

    def get(self):
        """ 任务大厅-字切分审定 """
        self.show_tasks('char_cut_review')
