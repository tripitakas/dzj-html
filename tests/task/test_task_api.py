#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from bson.objectid import ObjectId
from tests import users as u
from tests.testcase import APITestCase
from tests.task.conf import ready_ids, unready_ids, task_types
from controller import errors
from controller.helper import prop
from controller.task.base import TaskHandler as Th


class TestTaskApi(APITestCase):
    def setUp(self):
        super(TestTaskApi, self).setUp()
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
        super(TestTaskApi, self).tearDown()

    def assert_status(self, pages, response, task2status, msg=None):
        for task_type, status in task2status.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    def test_get_ready_tasks(self):
        """ 测试获取已就绪的任务列表 """
        for task_type in task_types:
            r = self.fetch('/api/task/ready/%s' % task_type, body={'data': {}})
            data = self.parse_response(r)
            self.assertIn('docs', data)

    def test_publish_tasks_by_doc_ids(self):
        """ 测试发布任务 """
        # 1. 测试异常情况
        # 测试任务类型有误
        data = dict(task_type='error_task_type', doc_ids=ready_ids)
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('task_type', r['error'])

        # 测试页面为空
        data = dict(task_type=task_types[0], doc_ids='')
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('doc_ids', r['error'])

        # 测试优先级有误（必须为1/2/3）
        data = dict(task_type=task_types[0], doc_ids=ready_ids, priority='高')
        r = self.parse_response(self.publish_page_tasks(data))
        self.assertIn('priority', r['error'])

        # 2. 测试正常情况
        for task_type in task_types:
            # 获取任务的meta信息
            collection, id_name, input_field, shared_field = Th.get_data_conf(task_type)
            meta = Th.task_types.get(task_type)

            # 测试数据不存在
            docs_un_existed = ['not_existed_1', 'not_existed_2']
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_un_existed)))
            self.assert_status(docs_un_existed, r, {task_type: 'un_existed'})

            # 测试数据未就绪。（只有任务依赖于某个数据字段，才有未就绪的情况）
            docs_un_ready = unready_ids
            if input_field:
                self._app.db[collection].update_many({id_name: {'$in': docs_un_ready}}, {'$unset': {input_field: ''}})
                r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_un_ready)))
                self.assert_status(docs_un_ready, r, {task_type: 'un_ready'}, msg=task_type)

            # 测试数据已就绪。（任务依赖的数据字段不为空，或者任务不依赖某个数据字段，即数据已就绪）
            docs_ready = ready_ids
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_ready)))
            status = 'published' if not meta.get('pre_tasks') else 'pending'
            self.assert_status(docs_ready, r, {task_type: status}, msg=task_type)

            # 测试已发布的任务，不能重新发布
            docs_published_before = list(docs_ready)
            r = self.parse_response(
                self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_published_before)))
            self.assert_status(docs_published_before, r, {task_type: 'published_before'})

            # 测试已退回的任务，可以重新发布
            docs_returned = list(docs_published_before)
            self._app.db.task.update_many({'doc_id': {'$in': docs_returned}}, {'$set': {'status': 'returned'}})
            condition = dict(task_type=task_type, doc_ids=docs_returned)
            r = self.parse_response(self.publish_page_tasks(condition))
            status = 'published' if not meta.get('pre_tasks') else 'pending'
            self.assert_status(docs_returned, r, {task_type: status}, msg=task_type)

            # 测试已完成的任务，可以强制重新发布
            docs_finished = list(docs_published_before)
            self._app.db.task.update_many({'doc_id': {'$in': docs_finished}}, {'$set': {'status': 'finished'}})
            condition = dict(task_type=task_type, force='是', doc_ids=docs_finished)
            r = self.parse_response(self.publish_page_tasks(condition))
            status = 'published' if not meta.get('pre_tasks') else 'pending'
            self.assert_status(docs_returned, r, {task_type: status}, msg=task_type)

            # 清空任务，以不影响后续任务
            self._app.db.task.delete_many({'doc_id': {'$in': docs_finished}})

    def test_publish_tasks_by_file(self):
        """ 测试以文件方式发布任务 """
        self.add_first_user_as_admin_then_login()
        # 创建文件
        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        with open(filename, 'w') as f:
            for doc_id in ready_ids:
                f.write(doc_id + '\n')
        self.assertTrue(os.path.exists(filename))

        # 测试正常情况
        # task_types = ['cut_review']
        for task_type in task_types:
            # 获取任务的meta信息
            t = Th.task_types.get(task_type)
            pre_tasks = t.get('pre_tasks') or []
            body = dict(task_type=task_type, priority=1, pre_tasks=pre_tasks, force='0', batch='0')
            r = self.fetch('/api/task/publish/page', files=dict(ids_file=filename), body=dict(data=body))
            data = self.parse_response(r)
            status = 'published' if not t.get('pre_tasks') else 'pending'
            self.assertIn(status, data, msg=task_type)
            self.assertEqual(set(data.get(status)), set(ready_ids), msg=task_type)

            # 测试文件为空
            data = self.parse_response(self.fetch('/api/task/publish/page', files=dict(), body=body))
            self.assertIn('error', data, msg=task_type)

    def test_publish_tasks_by_prefix(self):
        # 测试正常情况
        # task_types = ['cut_review']
        for task_type in task_types:
            r = self.publish_page_tasks({"task_type": task_type, "prefix": ready_ids[1][:2]})
            self.assert_code(200, r)

    def test_publish_many_tasks(self, size=10000):
        """ 测试发布大规模任务 """
        # task_types = ['cut_review']
        for task_type in task_types:
            meta = Th.task_types.get(task_type)
            pages = self._app.db.page.find({}, {'name': 1}).limit(size)
            doc_ids = [page['name'] for page in pages]
            r = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, doc_ids=doc_ids)))
            status = 'published' if not meta.get('pre_tasks') else 'pending'
            self.assertIn(status, r['data'])

    def test_publish_tasks_with_output_field(self):
        """ 测试发布有output_field字段的任务"""
        self.login_as_admin()
        task_type = 'upload_cloud'
        output_field = Th.prop(Th.task_types, '%s.data.output_field' % task_type)
        # 初始化
        self._app.db.page.update_many({}, {'$set': {output_field: None}})
        self._app.db.page.update_one(
            {'name': ready_ids[0]},
            {'$set': {output_field: 'http://cloud.tripitakas.net/QL_25_16.png'}}
        )
        # 发布任务
        r = self.publish_page_tasks(dict(doc_ids=ready_ids, task_type=task_type, pre_tasks=[]))
        data = self.parse_response(r)
        self.assertEqual(ready_ids[0:1], data.get('finished_before'))

    def test_pick_and_return_task(self):
        """ 测试领取和退回任务 """
        # task_types = ['cut_proof']
        for task_type in task_types:
            self.delete_tasks_and_locks()
            # 发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(doc_ids=ready_ids, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})

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
            self.assert_code(errors.task_uncompleted[0], r, msg=task_type)

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

    def test_pick_task_of_group(self):
        """ 测试领取组任务 """
        for group_task, v in Th.task_groups.items():
            num = 1
            for task_type in v.get('groups'):
                # 发布任务
                self.login_as_admin()
                r = self.publish_page_tasks(dict(doc_ids=ready_ids, task_type=task_type, pre_tasks=[]))
                self.assert_code(200, r)

                # 测试领取组任务中的第二个任务时，报错：已领取该组的任务
                self.login(u.expert1[0], u.expert1[1])
                task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
                r = self.fetch('/api/task/pick/' + group_task, body={'data': {'task_id': task['_id']}})
                if num != 1:
                    self.assert_code(errors.group_task_duplicated[0], r, msg=task_type)

                # 完成任务
                self._app.db.task.update_one({'_id': ObjectId(task['_id'])}, {'$set': {'status': 'finished'}})
                num += 1

    def test_submit_pre_task(self):
        """测试前置任务完成时，更新后置任务的状态"""
        for task_type, v in Th.task_types.items():
            pre_tasks = v.get('pre_tasks')
            if pre_tasks:
                # 发布当前任务，状态应为悬挂
                self.login_as_admin()
                d = self.parse_response(self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids)))
                if task_type in ['text_proof_1', 'text_proof_2']:
                    continue
                self.assert_status(ready_ids, d, {task_type: 'pending'}, msg=task_type)

                # 发布所有前置任务
                for pre_task in pre_tasks:
                    r1 = self.publish_page_tasks(dict(task_type=pre_task, doc_ids=ready_ids, pre_tasks=[]))
                    self.assert_code(200, r1)
                    # 完成前置任务
                    task = self._app.db.task.find_one(dict(task_type=pre_task, doc_id=ready_ids[0]))
                    r2 = self.fetch('/api/task/finish/%s' % task['_id'], body={'data': {}})
                    self.assert_code(200, r2)

                # 当前任务状态应该已发布
                cur_task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
                self.assertEqual('published', cur_task['status'], msg=task_type)

    def test_republish_tasks(self):
        """ 测试管理员重新发布进行中的任务 """
        # task_types = ['cut_proof']
        for task_type in task_types:
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
            self.assert_code(200, r)
            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
            self.assertTrue(task, msg=task_type)
            self.login(u.expert1[0], u.expert1[1])
            d = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}}))
            self.assertIn('task_id', d, msg=task_type)
            # 管理员重新发布进行中任务
            self.login_as_admin()
            r = self.fetch('/api/task/republish/%s' % task['_id'], body={'data': {}})
            self.assert_code(200, r, msg=task_type)
            # 管理员不能重新发布已发布的任务
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
            r = self.fetch('/api/task/republish/%s' % task2['_id'], body={'data': {}})
            self.assert_code(errors.republish_only_picked_or_failed[0], r, msg=task_type)

            self.delete_tasks_and_locks()

    def test_delete_tasks(self):
        """ 测试管理员删除已发布或悬挂的任务 """
        # task_types = ['cut_proof']
        for task_type in task_types:
            # 管理员发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
            if task_type == 'cut_review':
                self.assert_code(200, r)

            # 管理员删除已发布的任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[-1]})
            r = self.fetch('/api/task/delete', body={'data': {'_ids': [task['_id']]}})
            self.assertEqual(1, self.parse_response(r).get('count'), msg=task_type)

            # 用户领取任务
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
            self.assertTrue(task, msg=task_type)
            self.login(u.expert1[0], u.expert1[1])
            d = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}}))
            self.assertIn('task_id', d, msg=task_type)

            # 管理员不能删除进行中的任务
            self.login_as_admin()
            r = self.fetch('/api/task/delete', body={'data': {'_ids': [task['_id']]}})
            self.assertEqual(0, self.parse_response(r).get('count'), msg=task_type)

            # 删除任务，以免干扰后续测试
            self.delete_tasks_and_locks()

    def test_assign_tasks(self):
        """ 测试管理员指派任务给某个用户 """
        # task_types = ['cut_review']
        for task_type in task_types:
            # 管理员发布任务
            self.login_as_admin()
            self.delete_tasks_and_locks()
            r1 = self.publish_page_tasks(dict(task_type=task_type, doc_ids=ready_ids, pre_tasks=[]))
            self.assert_code(200, r1)

            # 管理员指派任务时，用户没有任务对应的角色
            user1 = self._app.db.user.find_one({'email': u.user1[0]})
            task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[0]})
            data = {'tasks': [[str(task['_id']), task_type, task['doc_id']]], 'user_id': user1['_id']}
            r2 = self.fetch('/api/task/assign', body={'data': data})
            self.assertEqual(str(task['doc_id']), prop(self.parse_response(r2), 'unauthorized')[0], msg=task_type)

            # 管理员不能指派进行中的任务
            user2 = self._app.db.user.find_one({'email': u.expert1[0]})
            self._app.db.task.update_one({'_id': task['_id']}, {'$set': {'status': 'finished'}})
            data = {'tasks': [[str(task['_id']), task_type, task['doc_id']]], 'user_id': str(user2['_id'])}
            r3 = self.fetch('/api/task/assign', body={'data': data})
            self.assertEqual(str(task['doc_id']), prop(self.parse_response(r3), 'un_published')[0], msg=task_type)

            # 管理员指派已发布的任务给授权用户
            task2 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': ready_ids[1]})
            data = {'tasks': [[str(task2['_id']), task_type, task2['doc_id']]], 'user_id': str(user2['_id'])}
            r4 = self.fetch('/api/task/assign', body={'data': data})
            self.assertTrue(prop(self.parse_response(r4), 'assigned'), msg=task_type)
            self.assertEqual(str(task2['doc_id']), prop(self.parse_response(r4), 'assigned')[0], msg=task_type)

    def test_get_user_list(self):
        """ 测试获取用户列表 """
        self.login_as_admin()
        # task_types = ['cut_proof']
        for task_type in task_types:
            r = self.fetch('/api/user/list', body={'data': {}})
            self.assert_code(200, r, msg=task_type)

    def test_publish_import_image(self):
        """ 测试发布图片导入任务"""
        # 发布任务
        task_type = 'import_image'
        data = dict(task_type=task_type, import_dir='/srv/test/abc', redo='是', layout='上下一栏', source='分类')
        r = self.fetch('/api/task/publish/import', body={'data': self.init_data(data)})
        self.assert_code(200, r)

        # 测试可以删除已发布的任务
        task = self._app.db.task.find_one({'task_type': 'import_image', 'input.import_dir': data['import_dir']})
        r = self.fetch('/api/task/delete', body={'data': {'_ids': [str(task['_id'])]}})
        self.assertEqual(1, self.parse_response(r).get('count'), msg=task_type)

        # 发布任务
        task_type = 'import_image'
        data = dict(task_type=task_type, import_dir='/srv/test/xyz', redo='否', layout='上下一栏', source='分类')
        r = self.fetch('/api/task/publish/import', body={'data': self.init_data(data)})
        self.assert_code(200, r)

        # 测试不能删除已完成的任务
        task = self._app.db.task.find_one({'task_type': 'import_image', 'input.import_dir': data['import_dir']})
        self._app.db.task.update_one({'_id': task['_id']}, {'$set': {'status': 'finished'}})
        r = self.fetch('/api/task/delete', body={'data': {'_ids': [str(task['_id'])]}})
        self.assertEqual(0, self.parse_response(r).get('count'), msg=task_type)

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
