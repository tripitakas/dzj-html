#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tests.users as u
from controller import errors as e
from tests.testcase import APITestCase


class TestCutTask(APITestCase):

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
            docs_ready = ['YB_22_346', 'YB_22_389', 'QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733']
            r = self.publish_page_tasks(dict(doc_ids=docs_ready, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)

            # 领取任务
            self.login(u.expert1[0], u.expert1[1])
            name = 'YB_22_346'
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            self.assert_code(200, r)

            # 提交第一步：切分数据
            page = self._app.db.page.find_one({'name': name})
            data = self.get_boxes(page)
            r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
            self.assert_code(200, r, msg=task_type)

            # 提交第二步：字序
            data = self.get_chars_col(page)
            r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
            self.assert_code(200, r, msg=task_type)

            # 检查任务状态，应为已完成
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})
            self.assertEqual('finished', task['status'], msg=task_type)

    def test_cut_edit(self):
        """ 测试编辑切分数据"""
        self.login(u.expert1[0], u.expert1[1])
        name = 'YB_22_346'
        page = self._app.db.page.find_one({'name': name})
        # 测试第一步：修改切分数据
        page['chars'][0]['w'] += 1
        data = self.get_boxes(page)
        r = self.fetch('/api/page/cut_edit/' + name, body={'data': data})
        self.assert_code(200, r)

        # 测试第二步：修改字序
        data = self.get_chars_col(page)
        chars_col1 = data['chars_col'][0]
        cid1, cid2 = chars_col1[:2]
        chars_col1[0], chars_col1[1] = cid2, cid1
        r = self.fetch('/api/page/cut_edit/' + name, body={'data': data})
        self.assert_code(200, r)

    def test_cut_mode(self):
        """ 测试切分页面的几种模式"""
        name = 'YB_22_346'
        task_type, step = 'cut_proof', 'box'
        page = self._app.db.page.find_one({'name': name})
        # 发布任务，仅发布第一步
        self.login_as_admin()
        r = self.publish_page_tasks(dict(doc_ids=[name], task_type=task_type, steps=[step], pre_tasks=[]))
        self.assert_code(200, r)

        # 用户expert1领取指定的任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
        self.assert_code(200, r)

        # 用户expert1提交任务
        data = self.get_boxes(page)
        r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
        self.assert_code(200, r)
        task = self._app.db.task.find_one({'_id': task['_id']})
        self.assertEqual(task['status'], 'finished')

        # 测试专家expert2可进入edit页面
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/cut_edit/%s?_raw=1' % name)
        self.assert_code(200, r)

        # 测试用户expert1不能进入update页面
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/task/update/cut_proof/%s?_raw=1' % task['_id'])
        self.assert_code(e.data_is_locked, r)

        # 专家expert2离开时解锁
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/data/unlock/box/' + name, body={'data': {}})
        self.assert_code(200, r)

        # 测试用户expert1可进入update页面
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/task/update/cut_proof/%s?_raw=1' % task['_id'])
        self.assert_code(200, r)

        # 测试专家expert2无法进入edit页面
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/cut_edit/YB_22_346?_raw=1')
        self.assert_code(e.data_is_locked, r)

        # 用户expert1离开时解锁
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/data/unlock/box/' + name, body={'data': {}})
        self.assert_code(200, r)

        # 测试专家expert2可进入edit页面
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/cut_edit/%s?_raw=1' % name)
        self.assert_code(200, r)
