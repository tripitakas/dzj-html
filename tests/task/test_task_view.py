#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random
import tests.users as u
from tests.testcase import APITestCase
from datetime import datetime, timedelta
from controller.task.base import TaskHandler as Th
from tests.task import config as c


class TestTaskView(APITestCase):
    def setUp(self):
        super(TestTaskView, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,数据处理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1, u.user2, u.user3]],
            '普通用户,单元测试用户'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestTaskView, self).tearDown()

    def assert_status(self, pages, response, task_type_status_maps, msg=None):
        for task_type, status in task_type_status_maps.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    def test_task_list(self):
        """ 测试任务管理、任务大厅、我的任务列表页面 """
        # 发布任务
        self.login_as_admin()
        for task_type in Th.task_types:
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=c.page_names, pre_tasks=[]))
            self.assert_code(200, r, msg=task_type)

        # 领取并完成任务
        self.login(u.expert1[0], u.expert1[1])
        for task_type in Th.task_types:
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            self.assert_code(200, r, msg=task_type)
            self.finish_task(task['_id'])

        # 任务管理页面
        self.login_as_admin()
        r = self.fetch('/task/admin/page?_raw=1')
        self.assert_code(200, r)
        r = self.fetch('/task/admin/image?_raw=1')
        self.assert_code(200, r)

        # 任务大厅页面
        for task_type in Th.task_types:
            r = self.fetch('/task/lobby/%s?_raw=1' % task_type)
            self.assert_code(200, r, msg=task_type)
            d = self.parse_response(r)
            self.assertIn('tasks', d, msg=task_type)

        # 我的任务页面
        self.login(u.expert1[0], u.expert1[1])
        for task_type in Th.task_types:
            r = self.fetch('/task/my/%s?_raw=1' % task_type)
            self.assert_code(200, r)
            d = self.parse_response(r)
            self.assertIn('docs', d, msg=task_type)
