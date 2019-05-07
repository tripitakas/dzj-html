#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""

import re
from datetime import datetime
from tornado.escape import json_decode, to_basestring
from controller.base import DbError
from controller import errors
from controller.task.base import TaskHandler


class PublishTasksApi(TaskHandler):
    URL = r'/api/task/publish/@task_type'

    def post(self, task_type):
        """
        发布某个任务类型的任务。
        如果task_type包含“.”，表示任务的二级结构task_type.sub_task_type，如text_proof.1表示文字校对/校一
        """

        assert task_type in self.flat_task_types
        try:
            data = self.get_request_data()
            priority, task_pages = data.get('priority') or '高', data['pages'].split(',')
            pages = self.db.page.find({'name': {"$in": task_pages}})
            result = []
            for page in pages:
                if '.' in task_type:
                    types = task_type.split('.')
                    old_status = page.get(types[0], {}).get(types[1], {}).get('status')
                else:
                    old_status = page.get(task_type, {}).get('status')

                status = self.STATUS_UNREADY
                if old_status == self.STATUS_READY:
                    status = self.STATUS_PENDING if self.has_pre_task(page, task_type) \
                        else self.STATUS_OPENED
                result.append({'name': page['name'], 'status': status})

                if status != self.STATUS_UNREADY:
                    update_value = {
                        '%s.status' % task_type: status,
                        '%s.priority' % task_type: priority,
                        '%s.publish_time' % task_type: datetime.now(),
                        '%s.publish_user_id' % task_type: self.current_user['_id'],
                        '%s.publish_by' % task_type: self.current_user['name'],
                    }
                    r = self.db.page.update_one(dict(name=page['name']), {'$set': update_value})
                    if r.modified_count:
                        self.add_op_log('publish_' + task_type, file_id=str(page['_id']), context=page['name'])

            self.send_response(result)

        except DbError as e:
            self.send_db_error(e)

    def has_pre_task(self, page, task_type):
        """
        检查任务是否包含待完成的前置任务
        """
        pre = self.pre_tasks.get(task_type, [])
        for t in pre:
            types = t.split('.')
            node = page.get(types[0], {}).get(types[1], {}) if len(types) > 1 else page.get(t, {})
            if node.get('status') not in [None, self.STATUS_READY, self.STATUS_FINISHED]:
                return True


class GetTaskApi(TaskHandler):
    URL = r'/api/@task_type/@task_id'

    def get(self, task_type, task_id):
        """ 获取单页数据 """
        try:
            page = self.db.page.find_one(dict(name=task_id))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(page)
        except DbError as e:
            self.send_db_error(e)


class GetLobbyTasksApi(TaskHandler):
    URL = r'/api/task/lobby/@task_type'

    def get(self, task_type):
        """ 任务大厅任务列表 """

        assert task_type in self.task_types.keys()
        try:
            page_no = self.get_query_argument('page_no', 1)
            page_size = self.get_query_argument('page_size', self.config['pager']['page_size'])

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
    URL = r'/api/page/@task_id'

    def get(self, name):
        """ 获取页面数据 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error(errors.no_object)
            self.send_response(page)
        except DbError as e:
            self.send_db_error(e)


class GetPagesApi(TaskHandler):
    URL = r'/api/pages/@page_kind'

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
                data = self.get_request_data()
                assert data.get('task_type') in all_types

                pages = self.db.page.find({data['task_type'] + '.status': self.STATUS_READY})
                self.send_response([p['name'] for p in pages])
            else:
                pages = [p for p in self.db.page.find({})
                         if [t for t in all_types if p.get(t + '.status')]]
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
    URL = '/api/unlock/@task_type/@page_prefix'

    def get(self, task_type, prefix=None):
        """ 退回全部任务 """
        types = task_type.split('.')
        try:
            pages = self.db.page.find(dict(name=re.compile('^' + prefix)) if prefix else {})
            ret = []
            for page in pages:
                info, unset = {}, {}
                name = page['name']
                for field in page:
                    if field in self.task_types and types[0] in field:
                        self.unlock(page, field, types, info, unset)
                if info:
                    r = self.db.page.update_one(dict(name=name), {'$set': info, '$unset': unset})
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_response(ret)
        except DbError as e:
            self.send_db_error(e)

    def unlock(self, page, field, types, info, unset):
        if self.task_types[field].get('sub_task_types'):
            for sub_task, v in page[field].items():
                if len(types) > 1 and types[1] != sub_task:
                    continue
                if v.get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
                    info[field + '.' + sub_task + '.status'] = self.STATUS_READY
                    unset[field + '.' + sub_task + '.user'] = None
        if page[field].get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
            info[field + '.status'] = self.STATUS_READY
            unset[field + '.user'] = None


class PickTaskApi(TaskHandler):
    def pick(self, task_type, name):
        """ 取审校任务 """
        try:
            # 有未完成的任务则不能继续
            task_user = task_type + '.picked_user_id'
            task_status = task_type + '.status'
            names = list(self.db.page.find({task_user: self.current_user['_id'], task_status: self.STATUS_LOCKED}))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error(errors.task_uncompleted, reason=','.join(names))

            # 领取新任务(待领取或已退回时)或继续原任务
            can_lock = {
                task_user: None,
                'name': name,
                '$or': [{task_status: self.STATUS_OPENED}, {task_status: self.STATUS_RETURNED}]
            }
            lock = {
                task_user: self.current_user['_id'],
                task_type + '.picked_by': self.current_user['name'],
                task_status: self.STATUS_LOCKED,
                task_type + '.start_time': datetime.now()
            }
            r = self.db.page.update_one(can_lock, {'$set': lock})
            page = self.db.page.find_one(dict(name=name))

            if r.matched_count:
                self.add_op_log('pick_' + task_type, file_id=page['_id'], context=name)
            elif page and page.get(task_user) == self.current_user['_id'] \
                    and page.get(task_status) == self.STATUS_LOCKED:
                self.add_op_log('open_' + task_type, file_id=page['_id'], context=name)
            else:
                # 被别人领取或还未就绪，就将只读打开(没有name)
                return self.send_response() if page else self.send_error(errors.no_object)

            # 反馈领取成功
            assert page.get(task_status) == self.STATUS_LOCKED
            self.send_response(dict(name=page['name']))
        except DbError as e:
            self.send_db_error(e)


class PickCutProofTaskApi(PickTaskApi):
    URL = '/api/pick/@box-type_cut_proof/@task_id'

    def get(self, kind, name):
        """ 取切分校对任务 """
        self.pick(kind + '_cut_proof', name)


class PickCutReviewTaskApi(PickTaskApi):
    URL = '/api/pick/@box-type_cut_review/@task_id'

    def get(self, kind, name):
        """ 取切分审定任务 """
        self.pick(kind + '_cut_review', name)


class PickTextProofTaskApi(PickTaskApi):
    URL = '/api/pick/text_proof_(1|2|3)/@task_id'

    def get(self, kind, name):
        """ 取文字校对任务 """
        self.pick('text_proof_%s' % kind, name)


class PickTextReviewTaskApi(PickTaskApi):
    URL = '/api/pick/text_review/@task_id'

    def get(self, name):
        """ 取文字审定任务 """
        self.pick('text_review', name)


class SaveCutApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_request_data()
            assert re.match(r'^[A-Za-z0-9_]+$', data.get('name'))
            assert re.match(self.re_cut_type, task_type)

            page = self.db.page.find_one(dict(name=data['name']))
            if not page:
                return self.send_error(errors.no_object)

            status = page.get(task_type + '.status')
            if status != self.STATUS_LOCKED:
                return self.send_error(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.user'
            if page.get(task_user) != self.current_user['_id']:
                return self.send_error(errors.task_locked)

            result = dict(name=data['name'])
            self.change_box(result, page, data['name'], task_type)
            if data.get('submit'):
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
                self.add_op_log('save_' + task_type, file_id=page['_id'], context=name)
                result['box_changed'] = True

    def submit_task(self, result, data, page, task_type, task_user):
        end_info = {task_type + '.status': self.STATUS_ENDED, task_type + '.end_time': datetime.now()}
        r = self.db.page.update_one({'name': data.name, task_user: self.current_user['_id']}, {'$set': end_info})
        if r.modified_count:
            result['submit'] = True
            self.add_op_log('submit_' + task_type, file_id=page['_id'], context=data.name)

            idx = self.task_types.index(task_type)
            for i in range(idx + 1, len(self.task_types)):
                next_status = self.task_types[i] + '.status'
                status = page.get(next_status)
                if status:
                    r = self.db.page.update_one({'name': data.name, next_status: self.STATUS_PENDING},
                                                {'$set': {next_status: self.STATUS_OPENED}})
                    if r.modified_count:
                        self.add_op_log('resume_' + task_type, file_id=page['_id'], context=data.name)
                        result['resume_next'] = True
                    break


class SaveCutProofApi(SaveCutApi):
    URL = '/api/save/@box-type_cut_proof'

    def post(self, kind):
        """ 保存或提交切分校对任务 """
        self.save(kind + '_cut_proof')


class SaveCutReviewApi(SaveCutApi):
    URL = '/api/save/@box-type_cut_review'

    def post(self, kind):
        """ 保存或提交切分审定任务 """
        self.save(kind + '_cut_review')
