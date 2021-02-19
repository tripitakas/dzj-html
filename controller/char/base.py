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
        """ 获取用户的数据等级"""
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
    def check_open_edit_role(cls, user_roles):
        if '文字专家' in user_roles or '文字审定员' in user_roles or '聚类审定员' in user_roles:
            return True
        else:
            return e.unauthorized[0], '需要文字审定员、聚类审定员或文字专家角色，您没有权限'

    @classmethod
    def check_txt_level_and_point(cls, self, char, task_type=None, response_error=True):
        """检查数据等级和积分"""
        # 1.检查数据等级。以任务数据等级优先，不够时检查用户数据等级
        r_level = cls.get_required_txt_level(char)
        u_level = cls.get_user_txt_level(self, task_type)
        if int(u_level) < int(r_level):
            msg = '该字符的文字数据等级为%s，%s数据等级%s不够' % (r_level, '当前任务' if task_type else '您的', u_level)
            return self.send_error_msg(e.data_level_unqualified[0], msg, response_error)
        # 2.检查权限
        roles = auth.get_all_roles(self.current_user['roles'])
        if '文字专家' in roles:
            return True
        r = cls.check_open_edit_role(roles)
        if r is not True:
            return self.send_error_msg(r[0], r[1], response_error)
        # 3. 检查积分
        task_types = list(cls.txt_level['task'].keys())
        if int(u_level) == int(r_level) and (not task_type or task_type not in task_types):
            if char.get('txt_logs') and char['txt_logs'][-1].get('user_id') == self.user_id:
                return True
            required_type, required_point = cls.get_required_type_and_point(char)
            user_point = cls.get_user_point(self, required_type)
            if int(user_point) < int(required_point):
                msg = '该字符需要%s的%s积分，您的积分%s不够' % (self.get_task_name(required_type), required_point, user_point)
                return self.send_error_msg(e.data_point_unqualified[0], msg, response_error)
        return True

    @staticmethod
    def get_base_field(task_type):
        """ 聚类任务以字数据的哪个字段进行聚类"""
        return 'cmb_txt' if 'proof' in task_type else 'rvw_txt'

    @classmethod
    def update_txt_equals(cls, db, batch, task_type=None):
        """ 设置聚类任务的文本相同程度"""
        cond = {'batch': batch, 'txt_equals': {'$in': [None, {}]}}
        task_type and cond.update({'task_type': task_type})
        tasks = list(db.task.find(cond, {'base_txts': 1, 'params': 1, 'task_type': 1}))
        print('[%s]update_txt_equals, %s tasks total' % (hp.get_date_time(), len(tasks)))
        for task in tasks:
            source = cls.prop(task, 'params.source')
            b_field = cls.get_base_field(task['task_type'])
            base_txts = [t['txt'] for t in task['base_txts']]
            print(str(task['_id']), source, base_txts)
            counts = list(db.char.aggregate([
                {'$match': {'source': source, b_field: {'$in': base_txts}}},
                {'$group': {'_id': '$sc', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            txt_equals = {str(c['_id']): c['count'] for c in counts}
            db.task.update_one({'_id': task['_id']}, {'$set': {'txt_equals': txt_equals}})
        print('finished.')

    @staticmethod
    def is_v_code(txt):
        return txt and len(txt) > 1 and txt[0] == 'v'

    def get_char_img(self, char):
        url = self.get_web_img(char.get('img_name') or char['name'], 'char')
        if url and char.get('img_time'):
            url += '?v=%s' % char['img_time']
        return url

    def get_user_argument(self, name, default=None):
        return self.get_query_argument(name, 0) or self.data.get(name, 0) or default

    def get_user_filter(self, task_type=None):
        """ 获取聚类校对的用户过滤条件"""

        def c2int(c):
            return int(float(c) * 1000)

        cond = {}
        # 按编码前缀
        name = self.get_user_argument('name', '')
        if name:
            cond.update({'name': {'$regex': name.upper()}})
        # 按校对字头
        txt = self.get_user_argument('txt', '')
        if txt:
            cond.update({'txt': txt})
        # 按相同程度、校对等级
        for f in ['sc', 'pc']:
            v = self.get_user_argument(f, 0)
            if v and re.match(r'^\d+$', v):
                cond[f] = int(v)
        # 按字置信度、列置信度
        for ac in ['cc', 'lc']:
            v = self.get_user_argument(ac, 0)
            if v:
                m1 = re.search(r'^([><]=?)(0|1|[01]\.\d+)$', v)
                m2 = re.search(r'^(0|1|[01]\.\d+),(0|1|[01]\.\d+)$', v)
                if m1:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m1.group(1))
                    cond.update({ac: {op: c2int(m1.group(2))} if op else v})
                elif m2:
                    cond.update({ac: {'$gte': c2int(m2.group(1)), '$lte': c2int(m2.group(2))}})
        # 按用户校对标记
        for f in ['is_vague', 'is_deform', 'uncertain']:
            v = self.get_user_argument(f, 0)
            if v == 'true':
                cond[f] = True
            elif v == 'false':
                cond[f] = {'$in': [None, False]}
        # 按是否备注过滤
        remark = self.get_user_argument('remark', 0)
        if remark == 'true':
            cond['remark'] = {'$nin': [None, '']}
        elif remark == 'false':
            cond['remark'] = {'$in': [None, '']}
        # 是否已提交
        submitted = self.get_user_argument('submitted', 0)
        if task_type and submitted == 'true':
            cond['tasks.' + task_type] = self.task['_id']
        elif task_type and submitted == 'false':
            cond['tasks.' + task_type] = {'$ne': self.task['_id']}
        # 按用户修改过滤
        updated = self.get_user_argument('updated', 0)
        if updated == 'my':
            cond['txt_logs.user_id'] = self.user_id
        elif updated == 'other':
            cond['txt_logs.user_id'] = {'$nin': [None, self.user_id]}
        elif updated == 'true':
            cond['txt_logs'] = {'$nin': [None, []]}
        elif updated == 'false':
            cond['txt_logs'] = {'$in': [None, []]}
        # 按数据等级过滤
        user_level = self.get_user_txt_level(self)
        task_level = self.get_user_txt_level(self, task_type)
        if updated == 'unauth':
            cond['txt_level'] = {'$gt': task_level if self.is_my_task else user_level}
        elif self.is_my_task:
            cond['txt_level'] = {'$lte': task_level}
        return cond
