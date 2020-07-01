#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 本模块测试发布任务以后，任务相关的公共api，包括：
# 1. 领取、退回、提交等用户操作;
# 2. 重新发布、删除、指派等管理员操作;
# 3. 定时回收超时任务等系统操作

from bson.objectid import ObjectId
from tests import users as u
from tests.testcase import APITestCase
from controller import errors as e
from controller import helper as hp
from datetime import datetime, timedelta
from controller.task.base import TaskHandler as Th
from periodic.republish_task import republish_timeout_tasks


class TestTaskApi(APITestCase):
    page_tasks = ['cut_proof', 'cut_review']
    page_names = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']

    def setUp(self):
        super(TestTaskApi, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,OCR加工员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1, u.user2, u.user3]],
            '普通用户,单元测试用户'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestTaskApi, self).tearDown()

    def test_pick_and_return_task(self):
        """ 测试领取和退回任务 """
        # self.page_tasks = ['cut_proof']
        for task_type in self.page_tasks:
            self.reset_tasks_and_data()
            # 发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(page_names=self.page_names, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[0]})

            # 领取指定的任务
            self.login(u.expert1[0], u.expert1[1])
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
            data = self.parse_response(r)
            self.assertIn('task_id', data, msg=task_type)
            task = self._app.db.task.find_one({'_id': ObjectId(data['task_id'])})
            self.assertEqual(task['status'], 'picked')
            self.assertEqual(task['picked_by'], u.expert1[2])

            # 领取第二个任务时，提示有未完成的任务
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {}})
            self.assert_code(e.task_uncompleted[0], r, msg=task_type)

            # 退回任务
            r = self.fetch('/api/task/return/%s' % task['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)

            # 再随机领取一个任务
            self.login(u.expert1[0], u.expert1[1])
            data = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {}}))
            self.assertIn('task_id', data, msg=task_type)
            task = self._app.db.task.find_one({'_id': ObjectId(data['task_id'])})
            self.assertEqual(task['status'], 'picked')
            self.assertEqual(task['picked_by'], u.expert1[2])

    def test_pick_task_of_num(self):
        """ 测试领取多个校次任务"""
        task_type, nums, page_name = 'cut_proof', [1, 2, 3], self.page_names[0]
        self.login_as_admin()
        # 发布多个校次的任务
        for num in nums:
            r = self.publish_page_tasks(dict(page_names=self.page_names, task_type=task_type, num=num, pre_tasks=[]))
            self.assert_code(200, r)

        # 领取第一个校次任务并完成任务
        self.login(u.expert1[0], u.expert1[1])
        task1 = self._app.db.task.find_one({'task_type': task_type, 'num': 1, 'doc_id': page_name})
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task1['_id']}})
        self.assert_code(200, r)
        self.finish_task(task1['_id'])

        # 测试领取第二个校次任务时报错：已领取该组的任务
        task2 = self._app.db.task.find_one({'task_type': task_type, 'num': 2, 'doc_id': page_name})
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task2['_id']}})
        self.assert_code(e.group_task_duplicated[0], r, msg=task_type)

    def test_update_post_tasks(self):
        """ 测试前置任务完成时，更新后置任务的状态"""
        # 发布切分审定任务
        self.login_as_admin()
        task_type, pre_tasks, page_name = 'cut_review', ['cut_proof'], self.page_names[0]
        d = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, page_names=self.page_names)))
        self.assert_status(self.page_names, d, {task_type: 'pending'}, msg=task_type)

        # 发布前置切分校对任务并完成任务
        for pre_task in pre_tasks:
            r = self.publish_page_tasks(dict(task_type=pre_task, page_names=self.page_names, pre_tasks=[]))
            self.assert_code(200, r)
            task1 = self._app.db.task.find_one(dict(task_type=pre_task, doc_id=page_name))
            r1 = self.finish_task(task1['_id'])
            self.assert_code(200, r1)

        # 当前任务状态应该已发布
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': page_name})
        self.assertEqual('published', task['status'])

    def test_republish_tasks(self):
        """ 测试管理员重新发布进行中的任务 """
        # self.page_tasks = ['cut_proof']
        for task_type in self.page_tasks:
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, page_names=self.page_names, pre_tasks=[]))
            self.assert_code(200, r)
            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[0]})
            self.assertTrue(task, msg=task_type)
            self.login(u.expert1[0], u.expert1[1])
            d = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}}))
            self.assertIn('task_id', d, msg=task_type)
            # 管理员重新发布进行中任务-成功
            self.login_as_admin()
            r = self.fetch('/api/task/republish/%s' % task['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            # 管理员重新发布已发布的任务-失败
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[0]})
            r = self.fetch('/api/task/republish/%s' % task2['_id'], body={'data': {}})
            self.assert_code(e.task_status_error[0], r, msg=task_type)

            self.reset_tasks_and_data()

    def test_delete_tasks(self):
        """ 测试管理员删除已发布或悬挂的任务 """
        # self.page_tasks = ['cut_proof']
        for task_type in self.page_tasks:
            self.reset_tasks_and_data()
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, page_names=self.page_names, pre_tasks=[]))
            self.assert_code(200, r)

            # 管理员删除已发布的任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[-1]})
            r = self.fetch('/api/task/delete', body={'data': {'_ids': [task['_id']]}})
            self.assertEqual(1, self.parse_response(r).get('count'), msg=task_type)

            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[0]})
            self.assertTrue(task, msg=task_type)
            self.login(u.expert1[0], u.expert1[1])
            d = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}}))
            self.assertIn('task_id', d, msg=task_type)

            # 管理员不能删除进行中的任务
            self.login_as_admin()
            r = self.fetch('/api/task/delete', body={'data': {'_ids': [task['_id']]}})
            self.assertEqual(0, self.parse_response(r).get('count'), msg=task_type)

    def test_assign_tasks(self):
        """ 测试管理员指派任务给某个用户 """
        # self.page_tasks = ['cut_review']
        for task_type in self.page_tasks:
            self.reset_tasks_and_data()
            # 管理员发布任务
            self.login_as_admin()
            r1 = self.publish_page_tasks(dict(task_type=task_type, page_names=self.page_names, pre_tasks=[]))
            self.assert_code(200, r1)

            # 管理员指派任务时，用户没有任务对应的角色
            user1 = self._app.db.user.find_one({'email': u.user1[0]})
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[0]})
            data = {'tasks': [[str(task['_id']), task_type, task['doc_id']]], 'user_id': user1['_id']}
            r2 = self.fetch('/api/task/assign', body={'data': data})
            self.assertEqual(str(task['doc_id']), hp.prop(self.parse_response(r2), 'unauthorized')[0], msg=task_type)

            # 管理员不能指派进行中的任务
            user2 = self._app.db.user.find_one({'email': u.expert1[0]})
            self._app.db.task.update_one({'_id': task['_id']}, {'$set': {'status': 'finished'}})
            data = {'tasks': [[str(task['_id']), task_type, task['doc_id']]], 'user_id': str(user2['_id'])}
            r3 = self.fetch('/api/task/assign', body={'data': data})
            self.assertEqual(str(task['doc_id']), hp.prop(self.parse_response(r3), 'un_published')[0], msg=task_type)

            # 管理员指派已发布的任务给授权用户
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.page_names[1]})
            data = {'tasks': [[str(task2['_id']), task_type, task2['doc_id']]], 'user_id': str(user2['_id'])}
            r4 = self.fetch('/api/task/assign', body={'data': data})
            self.assertTrue(hp.prop(self.parse_response(r4), 'assigned'), msg=task_type)
            self.assertEqual(str(task2['doc_id']), hp.prop(self.parse_response(r4), 'assigned')[0], msg=task_type)

    def test_init_tasks_for_op(self):
        """ 测试初始化任务，以便OP平台的测试"""
        self.login_as_admin()
        data = dict(import_dirs=['/home/file/base_dir@abc', '/home/file/base_dir@xyz'],
                    page_names=['GL_1056_5_6', 'YB_22_346'], layout='上下一栏')
        r = self.fetch('/api/task/init4op', body={'data': data})
        self.assert_code(200, r)

        # 测试已有图片导入任务
        condition = {'task_type': 'import_image', 'input.import_dir': {'$in': data['import_dirs']}}
        tasks = list(self._app.db.task.find(condition))
        self.assertTrue(len(tasks) >= 2)

        # 测试已有其它类型任务
        for task_type in ['ocr_box', 'ocr_text', 'upload_cloud']:
            condition = {'task_type': task_type, 'doc_id': {'$in': data['page_names']}}
            tasks = list(self._app.db.task.find(condition))
            self.assertTrue(len(tasks) >= 2)

    def test_republish_timeout_task(self):
        self.reset_tasks_and_data()
        # 发布任务，前置任务为空
        r = self.publish_page_tasks(dict(task_type='cut_proof', page_names=self.page_names, pre_tasks=[]))
        self.assert_code(200, r)

        # 领取任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': 'cut_proof', 'doc_id': self.page_names[0]})
        r = self.fetch('/api/task/pick/cut_proof', body={'data': {'task_id': task['_id']}})
        self.assertEqual(self.page_names[0], self.parse_response(r).get('doc_id'))
        task = self._app.db.task.find_one({'_id': task['_id']})
        self.assertEqual(task['picked_by'], u.expert1[2])

        # 修改发布时间
        update = {'picked_time': datetime.now() - timedelta(days=3)}
        self._app.db.task.update_one({'_id': task['_id']}, {'$set': update})

        # 测试自动回收任务
        republish_timeout_tasks(self._app.db, timeout_days=1, once_break=True)
        task = self._app.db.task.find_one({'_id': task['_id']})
        self.assertEqual(task['status'], Th.STATUS_PUBLISHED)
