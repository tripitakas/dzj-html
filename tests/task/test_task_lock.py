#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tornado.escape import json_encode
from tests.testcase import APITestCase
from controller import errors as e
from controller.task.base import TaskHandler as Th
from tests.task.conf import ready_ids, unready_ids, task_types


class TestDataLock(APITestCase):

    def setUp(self):
        super(TestDataLock, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2]],
            '切分专家,文字专家,数据管理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1]],
            '切分校对员,单元测试用户'
        )
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestDataLock, self).tearDown()

    def get_data_lock_and_level(self, doc_id, task_type):
        collection, id_name, input_field, shared_field = Th.get_data_conf(task_type)
        doc = self._app.db[collection].find_one({id_name: doc_id}) or {}
        return Th.prop(doc, 'lock.%s' % shared_field), int(Th.prop(doc, 'level.%s' % shared_field, 0))

    def test_data_lock_flow(self):
        """ 测试数据锁 """
        # task_types = ['cut_proof']
        for task_type in task_types:
            shared_field = Th.get_shared_field(task_type)
            if not shared_field:
                continue
            # 发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
            self.assert_code(200, r, msg=task_type)

            # 测试领取任务时，系统自动分配长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            task1 = self.get_one_task(task_type, ready_ids[0])
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task1['_id']}})
            self.assert_code(200, r, msg=task_type)
            conf_level = Th.get_conf_level(shared_field, task_type)
            lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
            self.assertListEqual([lock.get('locked_by'), lock.get('is_temp'), level], [u.expert1[2], False, conf_level])

            # 测试专家获得该数据锁时，提示已被其他人锁定
            self.login(u.expert2[0], u.expert2[1])
            r = self.fetch('/api/data/lock/%s/%s' % (shared_field, ready_ids[0]), body={'data': {}})
            self.assert_code(e.data_is_locked, r, msg=task_type)

            # 测试提交任务后，释放长时数据锁
            self.login(u.expert1[0], u.expert1[1])
            r = self.fetch('/api/task/finish/%s' % task1['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
            self.assertEqual(lock, {}, msg=task_type)

            # 测试专家获得临时数据锁
            self.login(u.expert2[0], u.expert2[1])
            r = self.fetch('/api/data/lock/%s/%s' % (shared_field, task1['doc_id']), body={'data': {}})
            self.assert_code(200, r, msg=task_type)

            # 专家离开时，解锁数据锁
            r = self.fetch('/api/data/unlock/%s/%s' % (shared_field, task1['doc_id']), body={'data': {}})
            self.assert_code(200, r, msg=task_type)

            # 用户获取临时数据锁
            self.login(u.expert1[0], u.expert1[1])
            r = self.fetch('/api/data/lock/%s/%s' % (shared_field, task1['doc_id']), body={'data': {}})
            self.assert_code(200, r, msg=task_type)

            # 专家此时不能获取临时数据锁
            self.login(u.expert2[0], u.expert2[1])
            r = self.fetch('/api/data/lock/%s/%s' % (shared_field, task1['doc_id']), body={'data': {}})
            self.assert_code(e.data_is_locked, r, msg=task_type)

            # 用户离开时，释放数据锁
            self.login(u.expert1[0], u.expert1[1])
            r = self.fetch('/api/data/unlock/%s/%s' % (shared_field, task1['doc_id']), body={'data': {}})
            self.assert_code(200, r, msg=task_type)

            # 领取第二个任务
            task2 = self.get_one_task(task_type, ready_ids[1])
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task2['_id']}})
            self.assert_code(200, r, msg=task_type)

            # 测试退回任务后，释放长时数据锁
            r = self.fetch('/api/task/return/%s' % task2['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            lock, level = self.get_data_lock_and_level(ready_ids[1], task_type=task_type)
            self.assertTrue(lock == {})

            self.delete_tasks_and_locks()

    def test_data_lock_special(self):
        """ 测试数据锁机制中的几种特殊情况 """
        # 发布切分校对任务
        self.login_as_admin()
        shared_field = 'box'
        task_type = 'cut_proof'
        r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
        self.assert_code(200, r, msg=task_type)

        # 用户3领取切分校对任务
        self.login(u.user1[0], u.user1[1])
        task1 = self.get_one_task(task_type, ready_ids[0])
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task1['_id']}})
        self.assert_code(200, r, msg=task_type)

        # 测试系统分配长时数据锁
        conf_level = Th.get_conf_level(shared_field, task_type)
        lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
        self.assertListEqual([lock.get('locked_by'), lock.get('is_temp'), level], [u.user1[2], False, conf_level])

        # 测试不能发布切分审定任务
        self.login_as_admin()
        r = self.publish_page_tasks(dict(task_type='cut_review', doc_ids=ready_ids, pre_tasks=[]))
        self.assertIn(ready_ids[0], self.parse_response(r).get('data_is_locked'))

        # 用户3完成任务
        self.login(u.user1[0], u.user1[1])
        r = self.fetch('/api/task/finish/%s' % task1['_id'], body={'data': {}})
        self.assert_code(200, r, msg=task_type)
        lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
        self.assertEqual(lock, {}, msg=task_type)

        # 测试发布切分审定任务
        self.login_as_admin()
        task_type = 'cut_review'
        r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
        self.assert_code(200, r, msg=task_type)

        # 用户2领取切分审定任务
        self.login(u.expert2[0], u.expert2[1])
        task2 = self.get_one_task(task_type, ready_ids[0])
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task2['_id']}})
        self.assert_code(200, r, msg=task_type)
        conf_level = Th.get_conf_level(shared_field, task_type)
        lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
        self.assertListEqual([lock.get('locked_by'), lock.get('is_temp'), level], [u.expert2[2], False, conf_level])

        # 用户2完成任务
        r = self.fetch('/api/task/finish/%s' % task2['_id'], body={'data': {}})
        self.assert_code(200, r, msg=task_type)
        lock, level = self.get_data_lock_and_level(ready_ids[0], task_type=task_type)
        self.assertEqual(lock, {}, msg=task_type)

        # 测试用户3数据等级不够，不能修改切分校对任务
        self.login(u.user1[0], u.user1[1])
        r = self.fetch('/task/update/cut_proof/%s?_raw=1' % task1['_id'])
        self.assertEqual(e.data_level_unqualified[0], self.parse_response(r).get('code'), msg=task_type)
        page = self._app.db.page.find_one({'name': ready_ids[0]})
        data = {'step': 'chars', 'submit': True, 'boxes': json_encode(page['chars'])}
        r = self.fetch('/api/task/update/cut_proof/%s' % task1['_id'], body={'data': data})
        self.assertEqual(e.data_level_unqualified[0], self.parse_response(r).get('code'), msg=task_type)

        # 测试用户2可以修改切分审定任务
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/task/update/cut_review/%s?_raw=1' % task2['_id'])
        self.assert_code(200, r, msg=task_type)
        self.assertFalse(self.parse_response(r).get('readonly'))
        r = self.fetch('/api/task/update/cut_review/%s' % task2['_id'], body={'data': data})
        self.assert_code(200, r, msg=task_type)
