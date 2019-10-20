#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from controller.periodic import periodic_task
from controller.task.base import TaskHandler as Th


class TestPeriodicTask(APITestCase):
    def setUp(self):
        super(TestPeriodicTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1]],
            '切分专家,文字专家'
        )
        self.delete_tasks_and_locks()

    def get_data_lock(self, task_type, page_name):
        page = self._app.db.page.find_one({'name': page_name})
        shared_field = Th.get_shared_field(task_type)
        return page and page.get('lock') and page.get('lock').get(shared_field)

    def test_do_task_release(self):
        self.login_as_admin()
        # 发布任务，前置任务为空
        task_type, page_name = 'text_review', 'GL_1056_5_6'
        self.assert_code(200, self.publish_tasks(dict(task_type=task_type, doc_ids=[page_name], pre_tasks=[])))
        task = self._app.db.task.find_one({'task_type': 'text_review', 'doc_id': page_name})

        # 领取任务
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/text_review', body={'data': {'doc_id': task['_id']}})
        self.assert_code(200, r)
        lock = self.get_data_lock(task_type, page_name)
        self.assertTrue(lock)
        self.assertEqual(lock.get('locked_by'), u.expert1[2])

        # 自动回收任务
        periodic_task(self._app, dict(at_once=True, minutes=1))
        self.assertTrue(self.get_data_lock(task_type, page_name))
        periodic_task(self._app, dict(at_once=True, minutes=0))
        # self.assertFalse(self.get_data_lock(task_type, page_name))
