#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .char import Char
from controller import auth
from controller.task.base import TaskHandler


class CharHandler(TaskHandler, Char):
    task_types = {
        'cluster_proof': {
            'name': '聚类校对', 'data': {'collection': 'char', 'id': 'name'},
            'num': [1, 2, 3],
        },
        'cluster_review': {
            'name': '聚类审定', 'data': {'collection': 'char', 'id': 'name'},
            'pre_tasks': ['cluster_proof'],
        },
        'separate_proof': {
            'name': '分类校对', 'data': {'collection': 'char', 'id': 'name'},
            'num': [1, 2, 3]
        },
        'separate_review': {
            'name': '分类审定', 'data': {'collection': 'char', 'id': 'name'},
            'pre_tasks': ['separate_proof'],
        },
    }

    role2level = {
        'box': dict(切分校对员=1, 切分审定员=10, 切分专家=100),
        'txt': dict(聚类校对员=1, 聚类审定员=10, 分类校对员=20, 分类审定员=30),
    }

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)

    def prepare(self):
        super().prepare()

    def get_char_count_by_task(self):
        char_tasks = list(self.db.task.find(
            {'collection': 'char', 'picked_user_id': self.user_id, 'status': self.STATUS_FINISHED},
            {'char_count': 1}
        ))
        char_count = sum([int(t.get('char_count', 0)) for t in char_tasks])
        return char_count

    def get_updated_char_count(self):
        return self.db.char.count_documents({'txt_logs.user_id': self.user_id})
