#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from bson.objectid import ObjectId
from tests import users as u
from tests.testcase import APITestCase
from controller import errors as e
from tests.task import config as c
from controller import helper as hp
from controller.task.base import TaskHandler as Th


class TestTaskApi(APITestCase):
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

    def assert_status(self, pages, response, task2status, msg=None):
        for task_type, status in task2status.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    def test_publish_page_tasks_by_doc_ids(self):
        """ 测试发布页任务 """
        # 1. 测试异常情况
        # 测试任务类型有误
        data = dict(task_type='error_task_type', page_names=c.page_names)
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('task_type', r['error'])

        # 测试页面为空
        data = dict(task_type=c.page_tasks[0], page_names='')
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('page_names', r['error'])

        # 测试优先级有误（必须为1/2/3）
        data = dict(task_type=c.page_tasks[0], page_names=c.page_names, priority='高')
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('priority', r['error'])

        # 2. 测试正常情况
        for task_type in c.page_tasks:
            # 测试数据不存在
            docs_un_existed = ['not_existed_1', 'not_existed_2']
            r = self.publish_page_tasks(dict(task_type=task_type, page_names=docs_un_existed))
            self.assert_code(e.not_allowed_empty, r)

            # 测试数据已就绪
            docs_ready = c.page_names
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
        self.add_first_user_as_admin_then_login()
        # 创建文件
        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        with open(filename, 'w') as f:
            for doc_id in c.page_names:
                f.write(doc_id + '\n')
        self.assertTrue(os.path.exists(filename))

        # 测试正常情况
        # c.page_tasks = ['cut_review']
        for task_type in c.page_tasks:
            pre_tasks = hp.prop(Th.task_types, '%s.pre_tasks' % task_type)
            status = 'published' if not pre_tasks else 'pending'
            body = dict(task_type=task_type, priority=1, pre_tasks=pre_tasks, force='0', batch='0')
            r = self.fetch('/api/page/task/publish', files=dict(names_file=filename), body=dict(data=body))
            data = self.parse_response(r)
            self.assertIn(status, data, msg=task_type)
            self.assertEqual(set(data.get(status)), set(c.page_names), msg=task_type)

            # 测试文件为空
            data = self.parse_response(self.fetch('/api/page/task/publish', files=dict(), body=body))
            self.assertIn('error', data, msg=task_type)

    def test_publish_tasks_by_prefix(self):
        # 测试正常情况
        # c.page_tasks = ['cut_review']
        for task_type in c.page_tasks:
            r = self.publish_page_tasks({"task_type": task_type, "prefix": c.page_names[1][:2]})
            self.assert_code(200, r)

    def test_publish_many_tasks(self, size=10000):
        """ 测试发布大规模任务 """
        # c.page_tasks = ['cut_review']
        for task_type in c.page_tasks:
            meta = Th.task_types.get(task_type)
            pages = self._app.db.page.find({}, {'name': 1}).limit(size)
            doc_ids = [page['name'] for page in pages]
            status = 'published' if not hp.prop(Th.task_types, '%s.pre_tasks' % task_type) else 'pending'
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, page_names=doc_ids)))
            self.assertIn(status, r['data'])

    def test_pick_and_return_task(self):
        """ 测试领取和退回任务 """
        # c.page_tasks = ['cut_proof']
        for task_type in c.page_tasks:
            self.reset_tasks_and_data()
            # 发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(page_names=c.page_names, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})

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
        """ 测试领取组任务"""
        task_type, nums, page_name = 'cut_proof', [1, 2, 3], c.page_names[0]
        self.login_as_admin()
        # 发布多个校次的任务
        for num in nums:
            r = self.publish_page_tasks(dict(page_names=c.page_names, task_type=task_type, num=num, pre_tasks=[]))
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

    def test_submit_pre_task(self):
        """ 测试前置任务完成时，更新后置任务的状态"""
        # 发布切分审定任务
        self.login_as_admin()
        task_type, pre_tasks, page_name = 'cut_review', ['cut_proof'], c.page_names[0]
        d = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, page_names=c.page_names)))
        self.assert_status(c.page_names, d, {task_type: 'pending'}, msg=task_type)

        # 发布前置切分校对任务并完成任务
        for pre_task in pre_tasks:
            r = self.publish_page_tasks(dict(task_type=pre_task, page_names=c.page_names, pre_tasks=[]))
            self.assert_code(200, r)
            task1 = self._app.db.task.find_one(dict(task_type=pre_task, doc_id=page_name))
            r1 = self.finish_task(task1['_id'])
            self.assert_code(200, r1)

        # 当前任务状态应该已发布
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': page_name})
        self.assertEqual('published', task['status'])

    def test_republish_tasks(self):
        """ 测试管理员重新发布进行中的任务 """
        # c.page_tasks = ['cut_proof']
        for task_type in c.page_tasks:
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, page_names=c.page_names, pre_tasks=[]))
            self.assert_code(200, r)
            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})
            self.assertTrue(task, msg=task_type)
            self.login(u.expert1[0], u.expert1[1])
            d = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}}))
            self.assertIn('task_id', d, msg=task_type)
            # 管理员重新发布进行中任务-成功
            self.login_as_admin()
            r = self.fetch('/api/task/republish/%s' % task['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            # 管理员重新发布已发布的任务-失败
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})
            r = self.fetch('/api/task/republish/%s' % task2['_id'], body={'data': {}})
            self.assert_code(e.task_status_error[0], r, msg=task_type)

            self.reset_tasks_and_data()

    def test_delete_tasks(self):
        """ 测试管理员删除已发布或悬挂的任务 """
        # c.page_tasks = ['cut_proof']
        for task_type in c.page_tasks:
            self.reset_tasks_and_data()
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, page_names=c.page_names, pre_tasks=[]))
            self.assert_code(200, r)

            # 管理员删除已发布的任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[-1]})
            r = self.fetch('/api/task/delete', body={'data': {'_ids': [task['_id']]}})
            self.assertEqual(1, self.parse_response(r).get('count'), msg=task_type)

            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})
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
        # c.page_tasks = ['cut_review']
        for task_type in c.page_tasks:
            self.reset_tasks_and_data()
            # 管理员发布任务
            self.login_as_admin()
            r1 = self.publish_page_tasks(dict(task_type=task_type, page_names=c.page_names, pre_tasks=[]))
            self.assert_code(200, r1)

            # 管理员指派任务时，用户没有任务对应的角色
            user1 = self._app.db.user.find_one({'email': u.user1[0]})
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[0]})
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
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': c.page_names[1]})
            data = {'tasks': [[str(task2['_id']), task_type, task2['doc_id']]], 'user_id': str(user2['_id'])}
            r4 = self.fetch('/api/task/assign', body={'data': data})
            self.assertTrue(hp.prop(self.parse_response(r4), 'assigned'), msg=task_type)
            self.assertEqual(str(task2['doc_id']), hp.prop(self.parse_response(r4), 'assigned')[0], msg=task_type)

    def test_init_tasks_for_test(self):
        """ 测试初始化任务，以便OP平台的测试"""
        self.login_as_admin()
        data = dict(import_dirs=['/home/file/base_dir@abc', '/home/file/base_dir@xyz'],
                    page_names=['GL_1056_5_6', 'YB_22_346'], layout='上下一栏')
        r = self.fetch('/api/task/init', body={'data': data})
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
