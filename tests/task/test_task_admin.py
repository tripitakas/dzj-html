#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tests.users as u
from controller import errors
from tests.testcase import APITestCase
from controller.task.base import TaskHandler as Th


class TestTaskPublish(APITestCase):
    def setUp(self):
        super(TestTaskPublish, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家'
        )
        self.delete_all_tasks()

    def tearDown(self):
        super(TestTaskPublish, self).tearDown()

    def assert_status(self, pages, response, task_type_status_maps, msg=None):
        for task_type, status in task_type_status_maps.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    def test_get_ready_tasks(self):
        """ 测试获取已就绪的任务列表 """
        task_types = list(Th.task_types.keys())
        for task_type in task_types:
            self.login_as_admin()
            r = self.fetch('/api/task/ready/%s' % task_type, body={'data': {}})
            data = self.parse_response(r)
            self.assertIn('docs', data)

    def test_publish_tasks(self):
        """ 测试发布任务 """
        self.add_first_user_as_admin_then_login()

        # 测试异常情况
        # 页面为空
        r = self.parse_response(self.publish_tasks(dict(task_type='cut_proof', doc_ids='')))
        self.assertIn('doc_ids', r['error'])

        # 任务类型有误
        doc_ids = 'GL_1056_5_6,JX_165_7_12'
        r = self.parse_response(self.publish_tasks(dict(task_type='error_task_type', doc_ids=doc_ids)))
        self.assertIn('task_type', r['error'])

        # 优先级有误，必须为1/2/3
        r = self.parse_response(self.publish_tasks(dict(task_type='cut_proof', doc_ids=doc_ids, priority='高')))
        self.assertIn('priority', r['error'])

        # 测试正常情况
        task_types = list(Th.task_types.keys())
        # task_types = ['text_review']
        for task_type in task_types:
            # 获取任务的meta信息
            t = Th.task_types.get(task_type)
            collection, id_name, input_field, shared_field = Th.task_meta(task_type)

            # 测试数据不存在
            docs_un_existed = ['not_existed_1', 'not_existed_2']
            r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(docs_un_existed))))
            self.assert_status(docs_un_existed, r, {task_type: 'un_existed'})

            # 测试数据未就绪。只有任务依赖于某个数据字段，才有未就绪的情况。
            docs_un_ready = ['JX_165_7_75', 'JX_165_7_87']
            if input_field:
                self._app.db[collection].update_many({id_name: {'$in': docs_un_ready}}, {'$unset': {input_field: ''}})
                r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(docs_un_ready))))
                self.assert_status(docs_un_ready, r, {task_type: 'un_ready'}, msg=task_type)

            # 测试数据已就绪。任务依赖的数据字段不为空，或者任务不依赖某个数据字段，即数据已就绪
            docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(docs_ready))))
            status = 'published' if not t.get('pre_tasks') else 'pending'
            self.assert_status(docs_ready, r, {task_type: status}, msg=task_type)

            # 测试已发布的任务，不能重新发布
            docs_published_before = list(docs_ready)
            r = self.parse_response(
                self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(docs_published_before))))
            self.assert_status(docs_published_before, r, {task_type: 'published_before'})

            # 测试已退回的任务，可以重新发布
            docs_returned = list(docs_published_before)
            self._app.db.task.update_many({'doc_id': {'$in': docs_returned}}, {'$set': {'status': 'returned'}})
            r = self.parse_response(
                self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(docs_returned))))
            status = 'published' if not t.get('pre_tasks') else 'pending'
            self.assert_status(docs_returned, r, {task_type: status}, msg=task_type)

    def test_publish_tasks_file(self):
        """ 测试以文件方式发布任务 """
        self.add_first_user_as_admin_then_login()
        # 创建文件
        pages = ['QL_25_733', 'YB_22_346']
        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        with open(filename, 'w') as f:
            for page in pages:
                f.write(page + '\n')
        self.assertTrue(os.path.exists(filename))

        # 测试正常情况
        task_types = list(Th.task_types.keys())
        # task_types = ['cut_review']
        for task_type in task_types:
            # 获取任务的meta信息
            t = Th.task_types.get(task_type)
            pre_tasks = t.get('pre_tasks') or []
            body = dict(task_type=task_type, priority=1, pre_tasks=pre_tasks, force='0')
            data = self.parse_response(
                self.fetch('/api/task/publish', files=dict(ids_file=filename), body=dict(data=body)))
            status = 'published' if not t.get('pre_tasks') else 'pending'
            self.assertIn(status, data, msg=task_type)
            self.assertEqual(set(data.get(status)), set(pages), msg=task_type)

            # 测试文件为空
            data = self.parse_response(self.fetch('/api/task/publish', files=dict(), body=body))
            self.assertIn('error', data, msg=task_type)

    def test_publish_many_tasks(self, size=10000):
        """ 测试发布大规模任务 """
        task_types = list(Th.task_types.keys())
        # task_types = ['cut_review']
        for task_type in task_types:
            t = Th.task_types.get(task_type)
            pages = self._app.db.page.find({}, {'name': 1}).limit(size)
            doc_ids = [page['name'] for page in pages]
            r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(doc_ids))))
            status = 'published' if not t.get('pre_tasks') else 'pending'
            self.assertIn(status, r['data'])

    def test_pick_task(self):
        """ 测试领取任务 """
        task_types = list(Th.task_types.keys())
        # task_types = ['cut_proof']
        for task_type in task_types:
            # 发布任务
            self.login_as_admin()
            docs_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            r = self.publish_tasks(dict(doc_ids=','.join(docs_ready), task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)

            # 领取第一个任务
            doc_id = docs_ready[0]
            self.login(u.expert1[0], u.expert1[1])
            data = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'doc_id': doc_id}}))
            self.assertEqual(doc_id, data.get('doc_id'), msg=task_type)
            task = self._app.db.task.find_one({'doc_id': doc_id})
            self.assertEqual(task['status'], 'picked')
            self.assertEqual(task['picked_by'], u.expert1[2])

            # 领取第二个任务时，报错，提示有未完成的任务
            r = self.fetch('/api/task/pick/' + task_type, body={'data': {'doc_id': docs_ready[1]}})
            self.assert_code(errors.task_uncompleted[0], r, msg=task_type)

    def test_retrieve_task(self):
        """ 测试管理员撤回任务 """
        for task_type in [
            'cut_proof', 'cut_review',
        ]:
            # 发布任务
            self.login_as_admin()
            doc_ids = ['GL_1056_5_6', 'JX_165_7_12', 'QL_25_16']
            doc_id = doc_ids[0]
            r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(doc_ids))))
            if 'proof' in task_type:
                # 用户领取任务
                self.login(u.expert1[0], u.expert1[1])
                r = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'doc_id': doc_id}}))
                self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
                self.login_as_admin()

            # 管理员撤回任务
            r = self.parse_response(self.fetch('/api/task/retrieve/%s/%s' % (task_type, doc_id), body={'data': {}}))
            self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
            page = self._app.db.page.find_one({'name': doc_id})
            self.assertIn(task_type, page['tasks'])
            self.assertEqual(page['tasks'][task_type]['status'], 'ready')
            data_field = Th.get_shared_field(task_type)
            if data_field:
                self.assertEqual(page['lock'][data_field], {})

    def test_reset_task(self):
        """ 测试管理员重置任务 """
        for task_type in [
            'cut_proof', 'cut_review',
        ]:
            # 重置未发布的任务
            self.login_as_admin()
            doc_ids = ['GL_1056_5_6', 'JX_165_7_12', 'QL_25_16']
            doc_id = doc_ids[0]
            r = self.parse_response(self.fetch('/api/task/delete/%s/%s' % (task_type, doc_id), body={'data': {}}))
            self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
            page = self._app.db.page.find_one({'name': doc_id})
            self.assertIn(task_type, page['tasks'])
            self.assertEqual(page['tasks'][task_type]['status'], 'unready')

            # 发布任务
            r = self.parse_response(self.publish_tasks(dict(task_type=task_type, doc_ids=','.join(doc_ids))))

            # 不能重置已发布的任务
            doc_id = 'GL_1056_5_6'
            r = self.fetch('/api/task/delete/%s/%s' % (task_type, doc_id), body={'data': {}})
            self.assert_code(errors.task_not_allowed_reset, r, msg=task_type)
