#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""

import re
from datetime import datetime
from functools import cmp_to_key
from tornado.escape import json_decode, to_basestring
from controller.handler.task import TaskHandler
from controller.handler.base import DbError
from controller.helper import convert_bson
from controller import errors

import model.user as u


class PublishTasksApi(TaskHandler):
    URL = r'/api/task/publish/(@task_type)'
    AUTHORITY = u.ACCESS_TASK_MGR

    def post(self, task_type):
        """
        发布任务。
        post提交的参数包括task_types/pages/priority。
        如果task_type包含“.”，表示任务的二级结构task_type.sub_task_type，如text_proof.1表示文字校对/校一
        """

        try:
            data = self.get_body_obj(PublishTask)
            task_types = list(set([t for t in data.types.split(',') if t in self.flat_types()]))
            task_pages = data.pages and data.pages.split(',')

            pages = self.db.page.find({'name': {"$in": task_pages}})
            publish_log = []
            for page in pages:
                update_value = {}
                for task_type in task_types:
                    assert isinstance(task_type, str)
                    status = self.STATUS_UNREADY
                    if '.' in task_type:
                        types = task_type.split('.')
                        if page.get(types[1], {}).get(types[2], {}).get('status') == self.STATUS_READY:
                            status = self.STATUS_OPENED if not self.has_pre_task(page['name'], task_type) \
                                else self.STATUS_PENDING
                            update_value.update({
                                r'%s.%s.status' % (types[1], types[2]): status,
                                r'%s.%s.priority' % (types[1], types[2]): data.priority,
                            })

                    else:
                        if page.get(task_type, {}).get('status') == self.STATUS_READY:
                            status = self.STATUS_OPENED if not self.has_pre_task(page['name'], task_type) \
                                else self.STATUS_PENDING
                            update_value.update({
                                r'%s.status' % task_type: status,
                                r'%s.priority' % task_type: data.priority,
                            })

                    publish_log.append({
                        'name': page['name'],
                        'task_type': task_type,
                        'status': status
                    })

                r = self.db.page.update_one(dict(name=page['name']), {'$set': update_value})
                if r.modified_count:
                    self.add_op_log('publish_' + task_type, file_id=str(page['_id']), context=page['name'])

            self.send_response(dict(publish_log=publish_log))
        except DbError as e:
            self.send_db_error(e)

    @staticmethod
    def has_pre_task(task_id, task_type):
        '''
        检查任务是否包含前置任务
        :param task_id: 对应page表的name字段
        :param task_type:
        :return: True/False
        '''
        pass


class GetTaskApi(TaskHandler):
    URL = r'/api/(@task_type)/(@task_id)'
    AUTHORITY = 'testing', 'any'

    def get(self, task_type, task_id):
        """ 获取单页数据 """
        try:
            page = self.db.page.find_one(dict(name=task_id))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(convert_bson(page))
        except DbError as e:
            self.send_db_error(e)


class GetLobbyTasksApi(TaskHandler):
    URL = r'/api/task/lobby/(@task_type)'
    AUTHORITY = 'testing', u.ACCESS_TASK_MGR

    def get(self, task_type):
        """ 任务大厅任务列表 """

        assert task_type in self.task_types.keys()
        try:
            page_no = self.get_query_argument('page_no', 1)
            page_size = self.get_query_argument('page_size', self.default_page_size)

            if 'sub_task_types' in self.task_types[task_type]:
                sub_types = self.task_types[task_type]['sub_task_types'].keys()
                conditions = {
                    '$or': [{'%s.%s.status' % (task_type, t): self.STATUS_PUBLISHED} for t in sub_types]
                }
                fields = {'name': 1}
                fields.update({'%s.%s.status' % (task_type, t): 1 for t in sub_types})
                fields.update({'%s.%s.priority' % (task_type, t): 1 for t in sub_types})
            else:
                conditions = {'%s.status' % task_type: self.STATUS_PUBLISHED}
                fields = {'name': 1}
                fields.update({'%s.status' % task_type: 1})
                fields.update({'%s.priority' % task_type: 1})

            pages = self.db.page.find(conditions, fields).limit(page_size).skip(page_size * (page_no - 1))
            self.send_response(pages)
        except DbError as e:
            self.send_db_error(e)


class GetPageApi(TaskHandler):
    URL = r'/api/page/([A-Za-z0-9_]+)'
    AUTHORITY = 'testing', 'any'

    def get(self, name):
        """ 获取页面数据 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(convert_bson(page))
        except DbError as e:
            self.send_db_error(e)


class GetPagesApi(TaskHandler):
    URL = r'/api/pages/([a-z_]+)'
    AUTHORITY = 'testing', u.ACCESS_TASK_MGR

    def get(self, kind):
        """ 为任务管理获取页面列表 """
        self.process(kind)

    def post(self, kind):
        """ 为任务管理获取页面列表 """
        self.process(kind)

    def process(self, kind):
        try:
            assert 'cut_' in kind or 'text_' in kind
            if 'cut_' in kind:
                all_types = ['block_cut_proof', 'column_cut_proof', 'char_cut_proof',
                             'block_cut_review', 'column_cut_review', 'char_cut_review']
            else:
                all_types = ['text_proof_1', 'text_proof_2', 'text_proof_3', 'text_review']

            if kind == 'cut_start' or kind == 'text_start':
                data = self.get_body_obj(PublishTask)
                task_types = [t for t in (data.types or '').split(',') if t in all_types]
                task_types = task_types or all_types

                pages = self.db.page.find({'$or': [{t + '_status': None} for t in task_types]})
                self.send_response([p['name'] for p in pages])
            else:
                pages = [convert_bson(p) for p in self.db.page.find({})
                         if [t for t in all_types if p.get(t + '_status')]]
                for p in pages:
                    for field, value in list(p.items()):
                        if field == 'txt':
                            p[field] = len(p[field])
                        elif isinstance(value, list):
                            del p[field]
                self.send_response(pages)
        except DbError as e:
            self.send_db_error(e)


class UnlockTasksApi(TaskHandler):
    URL = r'/api/unlock/(%s)/([A-Za-z0-9_]*)' % u.re_task_type + '|cut_proof|cut_review|cut|text'
    AUTHORITY = 'testing', u.ACCESS_TASK_MGR

    def get(self, task_type, prefix=None):
        """ 退回全部任务 """
        try:
            pages = self.db.page.find(dict(name=re.compile('^' + prefix)) if prefix else {})
            ret = []
            for page in pages:
                info = {}
                for field in page:
                    if re.match(u.re_task_type, field) and task_type in field:
                        info[field] = None
                if info:
                    name = page['name']
                    r = self.db.page.update_one(dict(name=name), {'$unset': info})
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_response(ret)
        except DbError as e:
            self.send_db_error(e)


class PublishTask(object):
    # 任务模型类，用于数据格式定义与转换
    types = str
    pages = str
    priority = str


class StartTasksApi(TaskHandler):
    URL = r'/api/start/([A-Za-z0-9_]*)'
    AUTHORITY = u.ACCESS_TASK_MGR

    def post(self, prefix=''):
        """ 发布审校任务 """
        try:
            data = self.get_body_obj(PublishTask)
            task_types = sorted(list(set([t for t in data.types.split(',') if t in u.task_types])),
                                key=cmp_to_key(lambda a, b: u.task_types.index(a) - u.task_types.index(b)))
            data.pages = data.pages and data.pages.split(',')

            # 得到待发布的页面
            pages = self.db.page.find(dict(name=re.compile('^' + prefix)) if prefix else {})
            names, items = set(), []
            for page in pages:
                name = page['name']
                if data.pages and name not in data.pages:
                    continue
                for i, task_type in enumerate(task_types):
                    task_status = task_type + '_status'
                    # 不重复发布任务
                    if page.get(task_status):
                        continue
                    # 是第一轮任务就为待领取，否则要等前一轮完成才能继续
                    status = u.STATUS_PENDING if i or self.has_pre_task(page, task_type) else u.STATUS_OPENED
                    new_value = {task_status: status, task_type + '_priority': data.priority}
                    r = self.db.page.update_one(dict(name=name), {'$set': new_value})
                    if r.modified_count:
                        self.add_op_log('start_' + task_type, file_id=str(page['_id']), context=name)
                        names.add(name)
                        items.append(dict(name=name, task_type=task_type, status=status))

            self.send_response(dict(names=list(names), items=items, task_types=task_types))
        except DbError as e:
            self.send_db_error(e)

    @staticmethod
    def has_pre_task(page, task_type):
        idx = u.task_types.index(task_type)
        for i in range(idx):
            status = page.get(u.task_types[i] + '_status')
            if status and status != u.STATUS_ENDED:
                return True


class PickTaskApi(TaskHandler):
    def pick(self, task_type, name):
        """ 取审校任务 """
        try:
            # 有未完成的任务则不能继续
            task_user = task_type + '_user'
            task_status = task_type + '_status'
            names = list(self.db.page.find({task_user: self.current_user.id, task_status: u.STATUS_LOCKED}))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error(errors.task_uncompleted, reason=','.join(names))

            # 领取新任务(待领取或已退回时)或继续原任务
            can_lock = {
                task_user: None,
                'name': name,
                '$or': [{task_status: u.STATUS_OPENED}, {task_status: u.STATUS_RETURNED}]
            }
            lock = {
                task_user: self.current_user.id,
                task_type + '_nickname': self.current_user.name,
                task_status: u.STATUS_LOCKED,
                task_type + '_start_time': datetime.now()
            }
            r = self.db.page.update_one(can_lock, {'$set': lock})
            page = convert_bson(self.db.page.find_one(dict(name=name)))

            if r.matched_count:
                self.add_op_log('pick_' + task_type, file_id=page['id'], context=name)
            elif page and page.get(task_user) == self.current_user.id and page.get(task_status) == u.STATUS_LOCKED:
                self.add_op_log('open_' + task_type, file_id=page['id'], context=name)
            else:
                # 被别人领取或还未就绪，就将只读打开(没有name)
                return self.send_response() if page else self.send_error(errors.no_object)

            # 反馈领取成功
            assert page.get(task_status) == u.STATUS_LOCKED
            self.send_response(dict(name=page['name']))
        except DbError as e:
            self.send_db_error(e)


class PickCutProofTaskApi(PickTaskApi):
    URL = r'/api/pick/(block|column|char)_cut_proof/([A-Za-z0-9_]+)'
    AUTHORITY = u.ACCESS_CUT_PROOF

    def get(self, kind, name):
        """ 取切分校对任务 """
        self.pick(kind + '_cut_proof', name)


class PickCutReviewTaskApi(PickTaskApi):
    URL = r'/api/pick/(block|column|char)_cut_review/([A-Za-z0-9_]+)'
    AUTHORITY = u.ACCESS_CUT_REVIEW

    def get(self, kind, name):
        """ 取切分审定任务 """
        self.pick(kind + '_cut_review', name)


class PickTextProofTaskApi(PickTaskApi):
    URL = r'/api/pick/text_proof_(1|2|3)/([A-Za-z0-9_]+)'
    AUTHORITY = u.ACCESS_TEXT_PROOF

    def get(self, kind, name):
        """ 取文字校对任务 """
        self.pick('text_proof_%s' % kind, name)


class PickTextReviewTaskApi(PickTaskApi):
    URL = r'/api/pick/text_review/([A-Za-z0-9_]+)'
    AUTHORITY = u.ACCESS_TEXT_REVIEW

    def get(self, name):
        """ 取文字审定任务 """
        self.pick('text_review', name)


class SaveTask(object):
    name = str
    submit = int


class SaveCutApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_body_obj(SaveTask)
            assert re.match(r'^[A-Za-z0-9_]+$', data.name)
            assert re.match(u.re_cut_type, task_type)

            page = convert_bson(self.db.page.find_one(dict(name=data.name)))
            if not page:
                return self.send_error(errors.no_object)

            status = page.get(task_type + '_status')
            if status != u.STATUS_LOCKED:
                return self.send_error(errors.task_changed, reason=u.task_statuses.get(status))

            task_user = task_type + '_user'
            if page.get(task_user) != self.current_user.id:
                return self.send_error(errors.task_locked)

            result = dict(name=data.name)
            self.change_box(result, page, data.name, task_type)
            if data.submit:
                self.submit_task(result, data, page, task_type, task_user)

            self.send_response(result)
        except DbError as e:
            self.send_db_error(e)

    def change_box(self, result, page, name, task_type):
        boxes = json_decode(self.get_body_argument('boxes', '[]'))
        box_type = to_basestring(self.get_body_argument('box_type', ''))
        field = box_type and box_type + 's'
        assert not boxes or box_type and field in page

        if boxes and boxes != page[field]:
            page[field] = boxes
            r = self.db.page.update_one({'name': name}, {'$set': {field: boxes}})
            if r.modified_count:
                self.add_op_log('save_' + task_type, file_id=page['id'], context=name)
                result['box_changed'] = True

    def submit_task(self, result, data, page, task_type, task_user):
        end_info = {task_type + '_status': u.STATUS_ENDED, task_type + '_end_time': datetime.now()}
        r = self.db.page.update_one({'name': data.name, task_user: self.current_user.id}, {'$set': end_info})
        if r.modified_count:
            result['submit'] = True
            self.add_op_log('submit_' + task_type, file_id=page['id'], context=data.name)

            idx = u.task_types.index(task_type)
            for i in range(idx + 1, len(u.task_types)):
                next_status = u.task_types[i] + '_status'
                status = page.get(next_status)
                if status:
                    r = self.db.page.update_one({'name': data.name, next_status: u.STATUS_PENDING},
                                                {'$set': {next_status: u.STATUS_OPENED}})
                    if r.modified_count:
                        self.add_op_log('resume_' + task_type, file_id=page['id'], context=data.name)
                        result['resume_next'] = True
                    break


class SaveCutProofApi(SaveCutApi):
    URL = r'/api/save/(block|column|char)_cut_proof'
    AUTHORITY = u.ACCESS_CUT_PROOF

    def post(self, kind):
        """ 保存或提交切分校对任务 """
        self.save(kind + '_cut_proof')


class SaveCutReviewApi(SaveCutApi):
    URL = r'/api/save/(block|column|char)_cut_review'
    AUTHORITY = u.ACCESS_CUT_REVIEW

    def post(self, kind):
        """ 保存或提交切分审定任务 """
        self.save(kind + '_cut_review')
