#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller import auth
from controller.data.data import Char
from controller.task.base import TaskHandler


class CharHandler(TaskHandler, Char):
    data_level = {
        'task': {'cluster_proof': 1, 'cluster_review': 10, 'separate_proof': 20, 'separate_review': 30},
        'role': {'聚类校对员': 1, '聚类审定员': 10, '分类校对员': 20, '分类审定员': 30},
    }

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)

    def prepare(self):
        super().prepare()

    def page_title(self):
        return self.task_name()

    def get_task_level(self, task_type):
        return self.prop(self.data_level['task'], task_type, 0)

    def get_user_level(self):
        user_roles = auth.get_all_roles(self.current_user['roles'])
        return max([self.data_level['role'].get(r, 0) for r in user_roles]) or 0

    def get_edit_level(self, edit_type):
        if edit_type == 'char_edit':
            return self.get_user_level()
        if edit_type in list(self.data_level['task'].keys()):
            return self.get_task_level(edit_type)

    def get_char_count_by_task(self):
        char_tasks = list(self.db.task.find(
            {'collection': 'char', 'picked_user_id': self.user_id, 'status': self.STATUS_FINISHED},
            {'char_count': 1}
        ))
        char_count = sum([int(t.get('char_count', 0)) for t in char_tasks])
        return char_count

    def get_updated_char_count(self):
        return self.db.char.count_documents({'txt_logs.user_id': self.user_id})
