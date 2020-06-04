#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from tests import users as u
from tests.testcase import APITestCase
from controller import errors as e
from controller import helper as hp
from controller.page.base import PageHandler as Ph
from controller.task.base import TaskHandler as Th


class TestPageTask(APITestCase):
    task_types = list(Ph.get_page_tasks().keys())
    page_names = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']

    def setUp(self):
        super(TestPageTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,数据管理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1, u.user2, u.user3]],
            '普通用户,单元测试用户'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestPageTask, self).tearDown()

    def test_publish_tasks_by_page_names(self):
        """ 测试发布页任务"""
        self.reset_tasks_and_data()
        # 1. 测试异常情况
        # 测试任务类型有误
        data = dict(task_type='error_task_type', page_names=self.page_names)
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('task_type', r['error'])

        # 测试页面为空
        data = dict(task_type=self.task_types[0], page_names='')
        r = self.publish_page_tasks(data)
        self.assert_code(e.not_allowed_empty, r)

        # 测试优先级有误（必须为1/2/3）
        data = dict(task_type=self.task_types[0], page_names=self.page_names, priority='高')
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('priority', r['error'])

        # 2. 测试正常情况
        for task_type in self.task_types:
            # 测试发布任务
            docs_ready = self.page_names
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, page_names=docs_ready)))
            status = 'published' if not hp.prop(Th.task_types, '%s.pre_tasks' % task_type) else 'pending'
            self.assert_status(docs_ready, r, {task_type: status}, msg=task_type)

            # 测试已发布的任务，不能重新发布
            docs_pub_before = list(docs_ready)
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, page_names=docs_pub_before)))
            self.assert_status(docs_pub_before, r, {task_type: 'published_before'})

            # 测试已退回的任务，可以重新发布
            docs_returned = list(docs_pub_before)
            self._app.db.task.update_many({'doc_id': {'$in': docs_returned}}, {'$set': {'status': 'returned'}})
            condition = dict(task_type=task_type, page_names=docs_returned)
            r = self.parse_response(self.publish_page_tasks(condition))
            self.assert_status(docs_returned, r, {task_type: status}, msg=task_type)

            # 测试已完成的任务，可以强制重新发布
            docs_finished = list(docs_pub_before)
            self._app.db.task.update_many({'doc_id': {'$in': docs_finished}}, {'$set': {'status': 'finished'}})
            condition = dict(task_type=task_type, force='1', page_names=docs_finished)
            r = self.parse_response(self.publish_page_tasks(condition))
            self.assert_status(docs_returned, r, {task_type: status}, msg=task_type)

            # 清空任务，以不影响后续任务
            self._app.db.task.delete_many({'doc_id': {'$in': docs_finished}})

    def test_publish_tasks_by_file(self):
        """ 测试以文件方式发布任务 """
        self.reset_tasks_and_data()
        self.add_first_user_as_admin_then_login()
        # 创建文件
        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        with open(filename, 'w') as f:
            for doc_id in self.page_names:
                f.write(doc_id + '\n')
        self.assertTrue(os.path.exists(filename))

        # 测试正常情况
        # self.task_types = ['cut_review']
        for task_type in self.task_types:
            pre_tasks = hp.prop(Th.task_types, '%s.pre_tasks' % task_type)
            status = 'published' if not pre_tasks else 'pending'
            body = dict(task_type=task_type, priority=1, pre_tasks=pre_tasks, force='0', batch='0')
            r = self.fetch('/api/page/task/publish', files=dict(names_file=filename), body=dict(data=body))
            data = self.parse_response(r)
            self.assertIn(status, data, msg=task_type)
            self.assertEqual(set(data.get(status)), set(self.page_names), msg=task_type)

            # 测试文件为空
            data = self.parse_response(self.fetch('/api/page/task/publish', files=dict(), body=body))
            self.assertIn('error', data, msg=task_type)

    def test_publish_tasks_by_prefix(self):
        # 测试正常情况
        self.reset_tasks_and_data()
        # self.task_types = ['cut_review']
        for task_type in self.task_types:
            r = self.publish_page_tasks({"task_type": task_type, "prefix": self.page_names[1][:2]})
            self.assert_code(200, r)

    def test_cut_task_flow(self):
        """ 测试切分任务流程 """
        for task_type in ['cut_proof', 'cut_review']:
            # 发布任务
            self.login_as_admin()
            page_names = ['YB_22_346', 'YB_22_389', 'QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733']
            r = self.publish_page_tasks(dict(page_names=page_names, task_type=task_type))
            self.assert_code(200, r)

            # 领取任务
            self.login(u.expert1[0], u.expert1[1])
            name = 'YB_22_346'
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            self.assert_code(200, r)

            # 提交第一步：切分数据
            page = self._app.db.page.find_one({'name': name})
            update = {k: page[k] for k in ['blocks', 'columns', 'chars']}
            data = {**update, 'step': 'box', 'submit': True}
            r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
            self.assert_code(200, r, msg=task_type)

            # 提交第二步：字序
            data = {'chars_col': Ph.get_chars_col(page['chars']), 'step': 'order', 'submit': True}
            r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
            self.assert_code(200, r, msg=task_type)

            # 检查任务状态，应为已完成
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})
            self.assertEqual('finished', task['status'], msg=task_type)
