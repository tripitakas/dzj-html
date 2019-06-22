#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from controller import errors
from controller.base import DbError
from controller.task.base import TaskHandler
from tornado.escape import json_decode


class SaveTextApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_request_data()
            assert re.match(r'^[A-Za-z0-9_]+$', data.get('name'))
            assert task_type in self.text_task_names()

            name = data['name']
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)

            status = self.prop(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.picked_user_id'
            page_user = self.prop(page, task_user)
            if page_user != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=name)

            result = dict(name=name)
            txt = data.get('txt') and re.sub(r'\|+$', '', json_decode(data['txt']).replace('\n', '|'))
            txt_field = task_type.replace('text_', 'text.')
            old_txt = self.prop(page, txt_field) or page['txt']
            if txt and txt != old_txt:
                assert isinstance(txt, str)
                result['changed'] = True
                self.db.page.update_one(dict(name=name), {'$set': {
                    txt_field: txt, '%s.last_updated_time' % task_type: datetime.now()
                }})
                self.add_op_log('save_' + task_type, file_id=page['_id'], context=name)

            if data.get('submit'):
                self.submit_task(result, data, page, task_type, pick_new_task=self.pick_new_task)

            self.send_data_response(result)
        except DbError as e:
            self.send_db_error(e)

    def pick_new_task(self, task_type):
        return self.get_lobby_tasks_by_type(task_type, page_size=1)


class SaveTextProofApi(SaveTextApi):
    URL = '/api/task/save/text_proof/@num'

    def post(self, num):
        """ 保存或提交文字校对任务 """
        self.save('text_proof.' + num)

    def pick_new_task(self, task_type):
        tasks = self.get_lobby_tasks_by_type('text_proof')
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
