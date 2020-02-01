#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random
import tests.users as u
from tests.testcase import APITestCase
from datetime import datetime, timedelta
from controller.task.base import TaskHandler as Th


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
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestTaskView, self).tearDown()

    def assert_status(self, pages, response, task_type_status_maps, msg=None):
        for task_type, status in task_type_status_maps.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    def test_view_task(self):
        """ 测试任务管理、任务大厅、我的任务列表页面 """
        # 发布任务
        self.login_as_admin()
        task_types = Th.get_doc_tasks('page')
        docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        for task_type in task_types:
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_ready, pre_tasks=[]))
            self.assert_code(200, r, msg=task_type)

        # 领取并完成任务
        self.login(u.expert1[0], u.expert1[1])
        task_types = ['cut_proof', 'cut_review', 'text_proof', 'text_review', 'text_hard']
        for task_type in task_types:
            task = self._app.db.task.find_one({'task_type': {'$regex': task_type + '.*'}, 'doc_id': docs_ready[0]})
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            self.assert_code(200, r, msg=task_type)
            r = self.fetch('/api/task/finish/%s' % task['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)

        # 任务管理页面
        self.login_as_admin()
        r = self.fetch('/task/admin/page?_raw=1')
        self.assert_code(200, r)
        r = self.fetch('/task/admin/image?_raw=1')
        self.assert_code(200, r)

        # 任务大厅页面
        for task_type in task_types:
            task_type = 'text_proof' if 'text_proof' in task_type else task_type
            r = self.fetch('/task/lobby/%s?_raw=1' % task_type)
            self.assert_code(200, r, msg=task_type)
            d = self.parse_response(r)
            self.assertIn('tasks', d, msg=task_type)

        # 我的任务页面
        self.login(u.expert1[0], u.expert1[1])
        for task_type in task_types:
            task_type = 'text_proof' if 'text_proof' in task_type else task_type
            r = self.fetch('/task/my/%s?_raw=1' % task_type)
            self.assert_code(200, r)
            d = self.parse_response(r)
            self.assertIn('docs', d, msg=task_type)

    def test_lobby_order(self):
        """测试任务大厅的任务显示顺序"""
        self.login_as_admin()
        self.publish_page_tasks(dict(task_type='text_proof_1', doc_ids=['GL_1056_5_6'], priority=2, pre_tasks=[]))
        self.publish_page_tasks(dict(task_type='text_proof_1', doc_ids=['JX_165_7_12'], priority=3, pre_tasks=[]))
        self.publish_page_tasks(dict(task_type='text_proof_2', doc_ids=['JX_165_7_12'], priority=2, pre_tasks=[]))
        self.publish_page_tasks(dict(task_type='text_proof_3', doc_ids=['JX_165_7_12'], priority=1, pre_tasks=[]))
        self.publish_page_tasks(dict(task_type='text_proof_2', doc_ids=['JX_165_7_30'], priority=1, pre_tasks=[]))

        self.login(u.expert1[0], u.expert1[1])
        for i in range(5):
            r = self.parse_response(self.fetch('/task/lobby/text_proof?_raw=1'))
            docs = [t['doc_id'] for t in r.get('tasks', [])]
            self.assertEqual(set(docs), {'GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30'})
            self.assertEqual(len(docs), len(set(docs)))  # 不同校次的同名页面只列出一个
            self.assertEqual(docs, ['JX_165_7_12', 'GL_1056_5_6', 'JX_165_7_30'])  # 按优先级顺序排列

    def add_local_statistic(self):
        docs = []
        users = list(self._app.db.user.find({}))
        task_types = ['upload_cloud', 'ocr_box', 'cut_proof', 'cut_review', 'ocr_text', 'text_proof_1',
                      'text_proof_2', 'text_proof_3', 'text_review', 'text_hard']

        today = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        for task_type in task_types:
            for i in range(10):
                day = today - timedelta(days=i)
                user = users[random.randint(0, len(users) - 1)]
                meta = dict(day=day, user_id=user['_id'], task_type=task_type, count=random.randint(0, 1000))
                docs.append(meta)
        self._app.db.statistic.insert_many(docs)
