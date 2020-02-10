#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import tests.users as u
from tests.testcase import APITestCase
from tornado.escape import json_encode


class TestCutTask(APITestCase):
    step2field = dict(chars='chars', columns='columns', blocks='blocks', orders='chars')

    def setUp(self):
        super(TestCutTask, self).setUp()
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
        super(TestCutTask, self).tearDown()

    def test_cut_task_flow(self):
        """ 测试切分任务流程 """
        for task_type in ['cut_proof', 'cut_review']:
            # 发布任务
            self.login_as_admin()
            docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            r = self.publish_page_tasks(dict(doc_ids=docs_ready, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)

            # 领取指定的任务
            self.login(u.expert1[0], u.expert1[1])
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': 'QL_25_16'})
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            self.assert_code(200, r)

            # 提交各步骤
            page = self._app.db.page.find_one({'name': 'QL_25_16'})
            steps = ['chars', 'blocks', 'columns', 'orders']
            for step in steps:
                data_field = self.step2field.get(step)
                data = {'step': step, 'submit': True, 'boxes': json_encode(page[data_field])}
                r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
                self.assert_code(200, r, msg=task_type + ':' + step)

            # 检查任务状态，应为已完成
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': 'QL_25_16'})
            self.assertEqual('finished', task['status'], msg=task_type)

    def test_cut_edit(self):
        """测试编辑切分数据"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试专家编辑提交数据
        page = self._app.db.page.find_one({'name': 'QL_25_16'})
        steps = ['chars', 'blocks', 'columns', 'orders']
        for step in steps:
            data_field = self.step2field.get(step)
            data = {'step': step, 'boxes': json_encode(page[data_field])}
            r = self.fetch('/api/data/cut_edit/QL_25_16', body={'data': data})
            self.assert_code(200, r, msg=step)

    def test_cut_mode(self):
        """测试切分页面的几种模式"""
        docs_ready = ['QL_25_16']
        task_type, step = 'cut_proof', 'chars'
        page = self._app.db.page.find_one({'name': 'QL_25_16'})
        # 发布任务
        self.login_as_admin()
        r = self.publish_page_tasks(dict(doc_ids=docs_ready, task_type=task_type, steps=[step], pre_tasks=[]))
        self.assert_code(200, r)

        # 用户expert1领取指定的任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': 'QL_25_16'})
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
        self.assert_code(200, r)

        # 用户expert1提交任务
        data = {'step': step, 'submit': True, 'boxes': json_encode(page['chars'])}
        r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
        self.assert_code(200, r)

        # 测试专家expert2进入edit页面时为可写
        self.login(u.expert2[0], u.expert2[1])
        r = self.parse_response(self.fetch('/data/cut_edit/QL_25_16?_raw=1'))
        self.assertEqual(False, r.get('readonly'))

        # 测试用户expert1进入update页面时为只读
        self.login(u.expert1[0], u.expert1[1])
        r = self.parse_response(self.fetch('/task/update/cut_proof/%s?_raw=1' % task['_id']))
        self.assertEqual(True, r.get('readonly'))

        # 专家expert2离开时解锁
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/data/unlock/box/QL_25_16', body={'data': {}})
        self.assert_code(200, r)

        # 测试用户expert1进入update页面时为可写
        self.login(u.expert1[0], u.expert1[1])
        r = self.parse_response(self.fetch('/task/update/cut_proof/%s?_raw=1' % task['_id']))
        self.assertEqual(False, r.get('readonly'))

        # 测试专家expert2进入edit页面时为只读
        self.login(u.expert2[0], u.expert2[1])
        r = self.parse_response(self.fetch('/data/cut_edit/QL_25_16?_raw=1'))
        self.assertEqual(True, r.get('readonly'))

        # 用户expert1离开时解锁
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/data/unlock/box/QL_25_16', body={'data': {}})
        self.assert_code(200, r)

        # 测试专家expert2进入edit页面时为可写
        self.login(u.expert2[0], u.expert2[1])
        r = self.parse_response(self.fetch('/data/cut_edit/QL_25_16?_raw=1'))
        self.assertEqual(False, r.get('readonly'))
