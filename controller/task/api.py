#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""

import re
from datetime import datetime
from tornado.escape import json_decode
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

            self.send_data_response(result)

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
                return self.send_error_response(errors.no_object)
            self.send_data_response(page)
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

            pages = self.db.page.find(conditions, fields).skip(page_size * (page_no - 1)).limit(page_size)
            self.send_data_response(pages)
        except DbError as e:
            self.send_db_error(e)


class GetPageApi(TaskHandler):
    URL = r'/api/page/@task_id'

    def get(self, name):
        """ 获取页面数据 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)
            self.send_data_response(page)
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
                self.send_data_response([p['name'] for p in pages])
            else:
                pages = [p for p in self.db.page.find({})
                         if [t for t in all_types if p.get(t + '.status')]]
                for p in pages:
                    for field, value in list(p.items()):
                        if field == 'txt':
                            p[field] = len(p[field])
                        elif isinstance(value, list):
                            del p[field]
                self.send_data_response(pages)
        except DbError as e:
            self.send_db_error(e)


class UnlockTasksApi(TaskHandler):
    URL = '/api/unlock/@task_type/@page_prefix'

    def get(self, task_type, prefix=None, returned=False):
        """ 退回全部任务 """
        types = task_type.split('.')
        try:
            # prefix为空找所有页面，prefix为6个以上字符为唯一匹配页面，其他则为页名前缀
            pages = self.db.page.find(dict(name=re.compile('^' + prefix) if len(prefix) < 6 else prefix
                                           ) if prefix else {})
            ret = []
            for page in pages:
                info, unset = {}, {}
                name = page['name']
                for field in page:
                    if field in self.task_types and types[0] in field:
                        self.unlock(page, field, types, info, unset, returned)
                if info:
                    r = self.db.page.update_one(dict(name=name), {'$set': info, '$unset': unset})
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_data_response(ret)
        except DbError as e:
            self.send_db_error(e)

    def post(self, task_type, prefix=None):
        """ 由审校者主动退回当前任务 """
        assert prefix and len(prefix) > 5
        page = self.db.page.find_one(dict(name=prefix))
        if not page:
            return self.send_error_response(errors.no_object)
        if PickTaskApi.page_get_prop(page, task_type + '.status') != self.STATUS_PICKED or \
                PickTaskApi.page_get_prop(page, task_type + '.picked_user_id') != self.current_user['_id']:
            return self.send_error_response(errors.task_locked, page_name=page['name'])
        self.get(task_type, prefix, returned=True)

    def unlock(self, page, field, types, info, unset, returned):
        def fill_info(field1):
            info['%s.status' % field1] = self.STATUS_RETURNED if returned else self.STATUS_READY
            info['%s.last_updated_time' % field1] = datetime.now()

        fields = ['picked_user_id', 'picked_by', 'picked_time', 'finished_time']
        if returned:
            fields.remove('picked_by')  # 在任务管理页面可看到原领取人
        if self.task_types[field].get('sub_task_types'):
            for sub_task, v in page[field].items():
                if len(types) > 1 and types[1] != sub_task:
                    continue
                if v.get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
                    fill_info(field + '.' + sub_task)
                    for f in fields:
                        unset[field + '.' + sub_task + '.' + f] = None
        if page[field].get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
            fill_info(field)
            for f in fields:
                unset[field + '.' + f] = None


class PickTaskApi(TaskHandler):
    def pick(self, task_type, name):
        """ 取审校任务 """
        try:
            # 有未完成的任务则不能继续
            task_user = task_type + '.picked_user_id'
            task_status = task_type + '.status'
            names = list(self.db.page.find({task_user: self.current_user['_id'], task_status: self.STATUS_PICKED}))
            names = [p['name'] for p in names]
            if names and name not in names:
                return self.send_error_response(errors.task_uncompleted,
                                                message='您有未完成的任务，不能领取新任务。是否继续未完成的任务(%s)？' % names[0],
                                                links=[('继续任务', '/task/do/%s/%s' % (task_type, names[0]))])
            # 领取新任务(待领取或已退回时)或继续原任务
            can_lock = {
                task_user: None,
                'name': name,
                '$or': [{task_status: self.STATUS_OPENED}, {task_status: self.STATUS_RETURNED}]
            }
            lock = {
                task_user: self.current_user['_id'],
                task_type + '.picked_by': self.current_user['name'],
                task_status: self.STATUS_PICKED,
                task_type + '.picked_time': datetime.now()
            }
            r = self.db.page.update_one(can_lock, {'$set': lock})
            page = self.db.page.find_one(dict(name=name))

            if r.matched_count:
                self.add_op_log('pick_' + task_type, file_id=page['_id'], context=name)
            elif page and self.page_get_prop(page, task_user) == self.current_user['_id'] \
                    and self.page_get_prop(page, task_status) == self.STATUS_PICKED:
                self.add_op_log('open_' + task_type, file_id=page['_id'], context=name)
            else:
                # 被别人领取或还未就绪，就将只读打开(没有name)
                return self.send_data_response() if page else self.send_error_response(errors.no_object)

            # 反馈领取成功
            self.send_data_response(dict(name=page['name']))
        except DbError as e:
            self.send_db_error(e)

    @staticmethod
    def page_get_prop(page, name):
        obj = page
        for s in name.split('.'):
            obj = obj and obj.get(s)
        return obj


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
            assert task_type in self.cut_task_names

            page = self.db.page.find_one(dict(name=data['name']))
            if not page:
                return self.send_error_response(errors.no_object)

            status = PickTaskApi.page_get_prop(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.picked_user_id'
            if PickTaskApi.page_get_prop(page, task_user) != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=page['name'])

            result = dict(name=data['name'])
            self.change_box(result, page, data, task_type)
            if data.get('submit'):
                self.submit_task(result, data, page, task_type, task_user)

            self.send_data_response(result)
        except DbError as e:
            self.send_db_error(e)

    def change_box(self, result, page, data, task_type):
        name = page['name']
        boxes = json_decode(data.get('boxes', '[]'))
        box_type = data.get('box_type')
        field = box_type and box_type + 's'
        assert not boxes or box_type and field in page

        if boxes and boxes != page[field]:
            page[field] = boxes
            time_field = '%s.last_updated_time' % task_type
            new_info = {field: boxes, time_field: datetime.now()}
            r = self.db.page.update_one({'name': name}, {'$set': new_info})
            if r.modified_count:
                self.add_op_log('save_' + task_type, file_id=page['_id'], context=name)
                result['box_changed'] = True
                result['updated_time'] = new_info[time_field]

    def submit_task(self, result, data, page, task_type, task_user):
        end_info = {
            task_type + '.status': self.STATUS_FINISHED,
            task_type + '.finished_time': datetime.now(),
            task_type + '.last_updated_time': datetime.now()
        }
        r = self.db.page.update_one({'name': page['name'], task_user: self.current_user['_id']}, {'$set': end_info})
        if r.modified_count:
            result['submitted'] = True
            self.add_op_log('submit_' + task_type, file_id=page['_id'], context=page['name'])

            # 激活后置任务，没有相邻后置任务则继续往后激活任务
            post_task = self.post_tasks.get(task_type)
            while post_task:
                next_status = post_task + '.status'
                status = PickTaskApi.page_get_prop(page, next_status)
                if status:
                    r = self.db.page.update_one({'name': page['name'], next_status: self.STATUS_PENDING},
                                                {'$set': {next_status: self.STATUS_OPENED}})
                    if r.modified_count:
                        self.add_op_log('resume_' + task_type, file_id=page['_id'], context=page['name'])
                        result['resume_next'] = post_task
                post_task = not status and self.post_tasks.get(post_task)

            # 随机分配新任务
            tasks = self.get_tasks_info_by_type(task_type, self.STATUS_OPENED, rand=True, sort=True)
            if tasks:
                name = tasks[0]['name']
                self.add_op_log('jump_' + task_type, file_id=tasks[0]['_id'], context=name)
                result['jump'] = '/task/do/%s/%s' % (task_type, name)


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
