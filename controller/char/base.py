#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .char import Char
from controller import auth
from controller.task.base import TaskHandler


class CharHandler(TaskHandler, Char):
    box_level = {
        'task': dict(cut_proof=1, cut_review=10),
        'role': dict(切分校对员=1, 切分审定员=10, 切分专家=100),
    }

    txt_level = {
        'task': dict(cluster_proof=1, cluster_review=10, separate_proof=20, separate_review=30),
        'role': dict(聚类校对员=1, 聚类审定员=10, 分类校对员=20, 分类审定员=30),
    }

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)

    def prepare(self):
        super().prepare()

    def get_box_level(self, kind, task_or_role):
        return self.prop(self.box_level, kind + '.' + task_or_role, 0)

    def get_txt_level(self, kind, task_or_role):
        return self.prop(self.txt_level, kind + '.' + task_or_role, 0)

    def get_user_level(self, field='box'):
        user_roles = auth.get_all_roles(self.current_user['roles'])
        if field == 'box':
            return max([self.get_box_level('role', r) for r in user_roles]) or 0
        if field == 'txt':
            return max([self.get_txt_level('role', r) for r in user_roles]) or 0

    def get_char_count_by_task(self):
        char_tasks = list(self.db.task.find(
            {'collection': 'char', 'picked_user_id': self.user_id, 'status': self.STATUS_FINISHED},
            {'char_count': 1}
        ))
        char_count = sum([int(t.get('char_count', 0)) for t in char_tasks])
        return char_count

    def get_updated_char_count(self):
        return self.db.char.count_documents({'txt_logs.user_id': self.user_id})
