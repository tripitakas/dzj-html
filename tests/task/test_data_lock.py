#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from controller.task.base import TaskHandler as Th

class TestDataLock(APITestCase):

    def setUp(self):
        super(TestDataLock, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        self.revert()

    def tearDown(self):
        super(TestDataLock, self).tearDown()

    def get_data_lock(self, page_name, task_type):
        page = self._app.db.page.find_one({'name': page_name})
        data_field = Th.get_shared_data_field(task_type)
        return page and data_field and page['lock'].get(data_field)

    def test_data_lock(self):
        """ 测试数据锁机制 """
        for task_type in [
            'block_cut_proof', 'block_cut_review',
            'column_cut_proof', 'column_cut_review',
            'char_cut_proof', 'char_cut_review'
        ]:
            # 发布任务，前置任务为空
            self.login_as_admin()
            self.revert()
            page_names = ['GL_1056_5_6', 'JX_165_7_12']
            self.assert_code(200, self.publish(dict(task_type=task_type, pre_tasks=[], pages=','.join(page_names))))

            # 测试领取任务时，系统自动分配长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            name1 = page_names[0]
            self.assert_code(200, self.fetch('/api/task/pick/'+ task_type, body={'data': {'page_name': name1}}))
            lock = self.get_data_lock(name1, task_type)
            self.assertListEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert1[2], False])

            # 测试保存任务时，数据锁不变
            self.assert_code(200, self.fetch('/api/task/do/%s/%s' % (task_type, name1), body={'data': {}}))
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert1[2], False])

            # 测试其它人无法获得数据锁
            self.login(u.expert2[0], u.expert2[1])
            data_field = Th.get_shared_data_field(task_type)
            self.fetch('/data/edit/%s/%s' % (data_field, name1))
            lock = self.get_data_lock(name1, task_type)
            self.assertNotEqual(lock.get('locked_by'), u.expert2[2])

            # 测试提交任务后，释放长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            self.assert_code(200, self.fetch('/api/task/do/%s/%s' % (task_type, name1),
                                             body={'data': {'submit': True}}))
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual(lock, {})

            # 测试用户update时，获取临时数据锁
            self.assert_code(200, self.fetch('/task/update/%s/%s' % (task_type, name1)))
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert1[2], True])

            # 释放临时数据锁
            r = self.fetch('/api/data/unlock/%s/%s' % (task_type, name1), body={'data': {}})
            self.assert_code(200, r)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual(lock, {})

            # 测试专家edit时，获取临时数据锁
            self.login(u.expert2[0], u.expert2[1])
            r = self.fetch('/data/edit/%s/%s' % (data_field, name1))
            self.assert_code(200, r)
            lock = self.get_data_lock(name1, task_type)
            self.assertEqual([lock.get('locked_by'), lock.get('is_temp')], [u.expert2[2], True])

            # 测试数据锁未释放时，其它人不能获取数据锁
            self.login(u.expert1[0], u.expert1[1])
            self.fetch('/data/edit/%s/%s' % (data_field, name1))
            lock = self.get_data_lock(name1, task_type)
            self.assertNotEqual(lock.get('locked_by'), u.expert1[2])

            # 领取第二个任务
            name2 = page_names[1]
            self.assert_code(200, self.fetch('/api/task/pick/' + task_type, body={'data': {'page_name': name2}}))

            # 测试退回任务后，释放长时数据锁
            self.assert_code(200, self.fetch('/api/task/return/%s/%s' % (task_type, name2), body={}))
            lock = self.get_data_lock(name2, task_type)
            self.assertEqual(lock, {})