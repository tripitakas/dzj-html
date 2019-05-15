#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from controller.base import DbError
from controller import errors
from controller.task.base import TaskHandler


class CharProofDetailHandler(TaskHandler):
    URL = '/task/do/text_proof/@num/@task_id'

    def get(self, proof_num, name=''):
        """ 进入文字校对页面 """
        self.enter(self, 'text_proof.' + proof_num, name, ('proof', '文字校对'))

    @staticmethod
    def enter(self, task_type, name, stage):
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.render('_404.html')

            cmp_data = dict(segments=[])
            picked_user_id = self.get_obj_property(page, task_type + '.picked_user_id')
            self.render('text_proof.html', page=page, name=page['name'], stage=stage,
                        origin_txt=re.split(r'\n|\|', page['txt'].strip()),
                        readonly=picked_user_id != self.current_user['_id'],
                        get_img=self.get_img, cmp_data=cmp_data)
        except Exception as e:
            self.send_db_error(e, render=True)


class CharReviewDetailHandler(TaskHandler):
    URL = '/task/do/text_review/@task_id'

    def get(self, name=''):
        """ 进入文字审定页面 """
        CharProofDetailHandler.enter(self, 'text_review', name, ('review', '文字审定'))


class SaveTextApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_request_data()
            assert re.match(r'^[A-Za-z0-9_]+$', data.get('name'))
            assert task_type in self.text_task_names

            page = self.db.page.find_one(dict(name=data['name']))
            if not page:
                return self.send_error_response(errors.no_object)

            status = self.get_obj_property(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.picked_user_id'
            page_user = self.get_obj_property(page, task_user)
            if page_user != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=page['name'])

            result = dict(name=data['name'])
            # self.change_box(result, page, data, task_type)
            if data.get('submit'):
                self.submit_task(result, data, page, task_type, task_user)

            self.send_data_response(result)
        except DbError as e:
            self.send_db_error(e)

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
            post_task = self.post_tasks().get(task_type)
            while post_task:
                next_status = post_task + '.status'
                status = self.get_obj_property(page, next_status)
                if status:
                    r = self.db.page.update_one({'name': page['name'], next_status: self.STATUS_PENDING},
                                                {'$set': {next_status: self.STATUS_OPENED}})
                    if r.modified_count:
                        self.add_op_log('resume_' + task_type, file_id=page['_id'], context=page['name'])
                        result['resume_next'] = post_task
                post_task = not status and self.post_tasks().get(post_task)

            task = self.pick_new_task(task_type)
            if task:
                self.add_op_log('jump_' + task_type, file_id=task['_id'], context=task['name'])
                result['jump'] = '/task/do/%s/%s' % (task_type.replace('.', '/'), task['name'])

    def pick_new_task(self, task_type):
        tasks = self.get_tasks_info_by_type(task_type, self.STATUS_OPENED, rand=True, sort=True)
        return tasks and tasks[0]


class SaveTextProofApi(SaveTextApi):
    URL = '/api/task/save/text_proof/@num'

    def post(self, num):
        """ 保存或提交文字校对任务 """
        self.save('text_proof.' + num)

    def pick_new_task(self, task_type):
        tasks = self.get_tasks_info_by_type('text_proof', self.STATUS_OPENED, rand=True, sort=True)
        picked = self.db.page.find({'$or': [
            {'text_proof.%d.picked_user_id' % i: self.current_user['_id']} for i in range(1, 4)
        ]}, {'name': 1})
        picked = [page['name'] for page in list(picked)]
        tasks = [t for t in tasks if t['name'] not in picked]
        return tasks and tasks[0]


class SaveTextReviewApi(SaveTextApi):
    URL = '/api/task/save/text_review'

    def post(self):
        """ 保存或提交文字审定任务 """
        self.save('text_review')
