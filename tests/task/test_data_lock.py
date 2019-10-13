#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from tornado.escape import json_encode
from controller.task.base import TaskHandler as Th


class TestDataLock(APITestCase):

    def setUp(self):
        super(TestDataLock, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        self.delete_all_tasks()

    def tearDown(self):
        super(TestDataLock, self).tearDown()

    def get_data_lock(self, page_name, task_type):
        page = self._app.db.page.find_one({'name': page_name})
        data_field = Th.get_shared_data(task_type)
        return page and data_field and page['lock'].get(data_field)

    def test_data_lock(self):
        """ 测试切分校对数据锁机制 """
        for task_type in [
            'cut_proof', 'cut_review',
            'text_review', 'text_hard',
        ]:
            # 发布任务，前置任务为空
            self.login_as_admin()
            self.delete_all_tasks()
            page_names = ['GL_1056_5_6', 'JX_165_7_12']
            data = dict(task_type=task_type, pre_tasks=[], pages=','.join(page_names))
            if 'cut' in task_type:
                data['steps'] = ['char_box']
            self.assert_code(200, self.publish_tasks(data))

            # 测试领取任务时，系统自动分配长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            name1 = page_names[0]
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'page_name': name1}})
            self.assert_code(200, r)
            lock = self.get_data_lock(name1, task_type)
            self.assertListEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert1[2], False])

            # 测试其它人无法获得数据锁
            edit_type = 'cut_edit' if 'cut' in task_type else 'text_edit'
            self.login(u.expert2[0], u.expert2[1])
            self.fetch('/data/%s/%s' % (edit_type, name1))
            lock = self.get_data_lock(name1, edit_type)
            self.assertNotEqual(lock.get('locked_by'), u.expert2[2])

            # 测试提交任务后，释放长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            page = self._app.db.page.find_one({'name': name1})
            data = {'step': 'char_box', 'submit': True, 'box_type': 'char', 'boxes': json_encode(page['chars'])}
            r = self.fetch('/api/task/do/%s/%s' % (task_type, name1), body={'data': data})
            self.assert_code(200, r, msg=task_type)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual(lock, {})

            # 测试用户update时，获取临时数据锁
            self.assert_code(200, self.fetch('/task/update/%s/%s' % (task_type, name1)), msg=task_type)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert1[2], True])

            # 释放临时数据锁
            r = self.fetch('/api/task/unlock/%s/%s' % (task_type, name1), body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual(lock, {})

            # 测试专家edit时，获取临时数据锁
            self.login(u.expert2[0], u.expert2[1])
            r = self.fetch('/data/%s/%s' % (edit_type, name1))
            self.assert_code(200, r)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert2[2], True], msg=task_type)

            # 测试数据锁未释放时，其它人不能获取数据锁
            self.login(u.expert1[0], u.expert1[1])
            self.fetch('/data/%s/%s' % (edit_type, name1))
            lock = self.get_data_lock(name1, task_type)
            self.assertNotEqual(lock.get('locked_by'), u.expert1[2])

            # 领取第二个任务
            name2 = page_names[1]
            self.assert_code(200, self.fetch('/api/task/pick/' + task_type, body={'data': {'page_name': name2}}))

            # 测试退回任务后，释放长时数据锁
            self.assert_code(200, self.fetch('/api/task/return/%s/%s' % (task_type, name2), body={}))
            lock = self.get_data_lock(name2, task_type)
            self.assertEqual(lock, {})
