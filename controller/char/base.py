#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .char import Char
from controller import auth
from controller import errors as e
from controller import helper as hp
from controller.task.base import TaskHandler


class CharHandler(Char, TaskHandler):
    txt_level = {
        'task': dict(text_proof=1, text_review=10, cluster_proof=1, cluster_review=10),
        'role': dict(文字校对员=1, 文字审定员=10, 聚类校对员=1, 聚类审定员=10, 文字专家=100),
    }
    default_level = 1

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)
        self.submit_by_page = True

    def prepare(self):
        super().prepare()

    @classmethod
    def get_required_txt_level(cls, char):
        return char.get('txt_level') or cls.default_level

    @classmethod
    def get_user_txt_level(cls, self, task_type=None, user=None):
        """获取用户的数据等级"""
        user = user or self.current_user
        task_types = list(cls.txt_level['task'].keys())
        if task_type and task_type in task_types:
            return hp.prop(cls.txt_level, 'task.' + task_type) or 0
        else:
            roles = auth.get_all_roles(user['roles'])
            return max([hp.prop(cls.txt_level, 'role.' + role, 0) for role in roles])

    @staticmethod
    def get_required_type_and_point(char):
        """计算修改char的txt所需的积分"""
        ratio = {'cluster_proof': 2000, 'cluster_review': 1000}
        for task_type in ['cluster_review', 'cluster_proof']:
            tasks = hp.prop(char, 'tasks.' + task_type, [])
            if tasks:
                return task_type, len(tasks) * ratio.get(task_type)
        return 'cluster_proof', 2000

    @staticmethod
    def get_user_point(self, task_type):
        """针对指定的任务类型，获取用户积分"""
        counts = list(self.db.task.aggregate([
            {'$match': {'task_type': task_type, 'status': self.STATUS_FINISHED, 'picked_user_id': self.user_id}},
            {'$group': {'_id': None, 'count': {'$sum': '$char_count'}}},
        ]))
        points = counts and counts[0]['count'] or 0
        return points

    @classmethod
    def check_txt_level_and_point(cls, self, char, task_type=None, send_error_response=True):
        """检查数据等级和积分"""
        required_level = cls.get_required_txt_level(char)
        user_level = cls.get_user_txt_level(self, task_type)
        if int(user_level) < int(required_level):
            msg = '该字符的文字数据等级为%s，您的文字数据等级%s不够' % (required_level, user_level)
            if send_error_response:
                return self.send_error_response(e.data_level_unqualified, message=msg)
            else:
                return e.data_level_unqualified[0], msg
        roles = auth.get_all_roles(self.current_user['roles'])
        if '文字专家' in roles:
            return True
        task_types = list(cls.txt_level['task'].keys())
        if int(user_level) == int(required_level) and (not task_type or task_type not in task_types):
            if char.get('txt_logs') and char['txt_logs'][-1].get('user_id') == self.user_id:
                return True
            required_type, required_point = cls.get_required_type_and_point(char)
            user_point = cls.get_user_point(self, required_type)
            if int(user_point) < int(required_point):
                msg = '该字符需要%s的%s积分，您的积分%s不够' % (self.get_task_name(required_type), required_point, user_point)
                if send_error_response:
                    return self.send_error_response(e.data_point_unqualified, message=msg)
                else:
                    return e.data_point_unqualified[0], msg
        return True

    def get_char_img(self, char):
        url = self.get_web_img(char.get('img_name') or char['name'], 'char')
        if url and char.get('img_time'):
            url += '?v=%s' % char['img_time']
        return url
