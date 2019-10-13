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
        self.revert()

    def tearDown(self):
        super(TestTaskPublish, self).tearDown()

    def assert_status(self, pages, response, task_type_status_maps):
        for task_type, status in task_type_status_maps.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages))

    def test_publish_tasks_common(self):
        """ 测试发布任务 """
        self.add_first_user_as_admin_then_login()

        """ 测试异常情况 """
        # 页面为空
        r = self.parse_response(self.publish(dict(task_type='cut_proof', pages='')))
        self.assertIn('pages', r['error'])

        # 任务类型有误
        pages = 'GL_1056_5_6,JX_165_7_12'
        r = self.parse_response(self.publish(dict(task_type='error_task_type', pages=pages)))
        self.assertIn('task_type', r['error'])

        # 优先级有误，必须为1/2/3
        r = self.parse_response(self.publish(dict(task_type='cut_proof', pages=pages, priority='高')))
        self.assertIn('priority', r['error'])

        # 测试正常情况
        for task_type in [
            'cut_proof', 'cut_review',
            'text_proof_1', 'text_proof_2', 'text_proof_3', 'text_review'
        ]:
            pages_un_existed = ['GL_not_existed_1', 'JX_not_existed_2']
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_un_existed))))
            self.assert_status(pages_un_existed, r, {task_type: 'un_existed'})

            # 测试未就绪的页面
            pages_un_ready = ['GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87']
            self.set_task_status({task_type: Th.TASK_UNREADY}, pages_un_ready)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_un_ready))))
            self.assert_status(pages_un_ready, r, {task_type: 'un_ready'})

            # 测试已就绪的页面
            pages_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            self.set_task_status({task_type: Th.TASK_READY}, pages_ready)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_ready))))
            status = 'published' if 'proof' in task_type else 'pending'
            self.assert_status(pages_ready, r, {task_type: status})

            # 测试已发布的页面
            pages_published_before = ['YB_22_916', 'YB_22_995']
            self.set_task_status({task_type: Th.TASK_OPENED}, pages_published_before)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_published_before))))
            self.assert_status(pages_published_before, r, {task_type: 'published_before'})

            # 组合测试
            all_pages = pages_un_existed + pages_un_ready + pages_ready + pages_published_before
            self.set_task_status({task_type: Th.TASK_UNREADY}, pages_un_ready)
            self.set_task_status({task_type: Th.TASK_READY}, pages_ready)
            self.set_task_status({task_type: Th.TASK_OPENED}, pages_published_before)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(all_pages))))
            self.assert_status(pages_un_existed, r, {task_type: 'un_existed'})
            self.assert_status(pages_un_ready, r, {task_type: 'un_ready'})
            self.assert_status(pages_ready, r, {task_type: status})
            self.assert_status(pages_published_before, r, {task_type: 'published_before'})

            # 还原页面状态
            self.set_task_status({task_type: Th.TASK_READY}, pages_un_ready)
            self.set_task_status({task_type: Th.TASK_READY}, pages_published_before)

    def test_publish_tasks_with_pre_tasks(self):
        """ 测试发布带前置任务的任务 """
        doc_ids = ['YB_22_713', 'YB_22_759', 'YB_22_816']
        for t, pre in self.pre_tasks.items():
            if pre:
                self.set_task_status({t: Th.TASK_READY}, doc_ids)
                if isinstance(pre, list):
                    pre = pre[0]
                self.set_task_status({pre: Th.TASK_READY}, doc_ids)
                r = self.parse_response(self.publish(dict(task_type=t, pages=','.join(doc_ids))))
                pending = r.get('data', {}).get('pending')
                self.assertEqual(set(doc_ids), set(pending))

    def test_publish_tasks_file(self):
        """ 测试以文件方式发布审校任务 """
        self.add_first_user_as_admin_then_login()
        # 创建文件
        pages = ['GL_1056_5_6', 'JX_165_7_12']
        self.set_task_status({'cut_proof': 'ready'}, pages)
        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        with open(filename, 'w') as f:
            for page in pages:
                f.write(page + '\n')
        self.assertTrue(os.path.exists(filename))

        # 测试正常发布
        task_type = 'cut_proof'
        steps = ['char_box', 'block_box', 'column_box', 'char_order']
        body = dict(task_type=task_type, priority=1, pre_tasks=self.pre_tasks.get(task_type, ''),
                    force='0', sub_steps=','.join(steps))
        r = self.parse_response(self.fetch('/api/task/publish', files=dict(pages_file=filename), body=body))
        self.assertEqual(set(r.get('published')), set(pages))

        # 测试任务类型有误
        task_type = 'error_task_type'
        body = dict(task_type=task_type, priority=1, pre_tasks=self.pre_tasks.get(task_type, ''),
                    force='0', sub_steps=','.join(steps))
        r = self.parse_response(self.fetch('/api/task/publish', files=dict(pages_file=filename), body=body))
        self.assertIn('task_type', r['error'])

    def test_publish_many_tasks(self, size=10000):
        """ 测试发布大规模任务 """
        for task_type in [
            'cut_proof', 'cut_review',
        ]:
            pages = self._app.db.page.find({}, {'name': 1}).limit(size)
            doc_ids = [page['name'] for page in pages]
            self.set_task_status({task_type: Th.TASK_READY}, doc_ids)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(doc_ids))))
            status = 'published' if 'proof' in task_type else 'pending'
            self.assertIn(status, r['data'])

    def test_withdraw_task(self):
        """ 测试管理员撤回任务 """
        for task_type in [
            'cut_proof', 'cut_review',
        ]:
            # 发布任务
            self.login_as_admin()
            doc_ids = ['GL_1056_5_6', 'JX_165_7_12', 'QL_25_16']
            doc_id = doc_ids[0]
            self.set_task_status({task_type: 'ready'}, doc_ids)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(doc_ids))))
            if 'proof' in task_type:
                # 用户领取任务
                self.login(u.expert1[0], u.expert1[1])
                r = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {'doc_id': doc_id}}))
                self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
                self.login_as_admin()

            # 管理员撤回任务
            r = self.parse_response(self.fetch('/api/task/withdraw/%s/%s' % (task_type, doc_id), body={'data': {}}))
            self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
            page = self._app.db.page.find_one({'name': doc_id})
            self.assertIn(task_type, page['tasks'])
            self.assertEqual(page['tasks'][task_type]['status'], 'ready')
            data_field = Th.get_shared_data(task_type)
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
            r = self.parse_response(self.fetch('/api/task/reset/%s/%s' % (task_type, doc_id), body={'data': {}}))
            self.assertEqual(doc_id, r.get('doc_id'), msg=task_type)
            page = self._app.db.page.find_one({'name': doc_id})
            self.assertIn(task_type, page['tasks'])
            self.assertEqual(page['tasks'][task_type]['status'], 'unready')

            # 发布任务
            self.set_task_status({task_type: 'ready'}, doc_ids)
            r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(doc_ids))))

            # 不能重置已发布的任务
            doc_id = 'GL_1056_5_6'
            r = self.fetch('/api/task/reset/%s/%s' % (task_type, doc_id), body={'data': {}})
            self.assert_code(errors.task_not_allowed_reset, r, msg=task_type)

    def test_get_read_tasks(self):
        """ 测试获取已就绪的任务列表 """
        for task_type in [
            'cut_proof', 'cut_review',
        ]:
            # 重置未发布的任务
            self.login_as_admin()
            r = self.fetch('/api/task/ready/%s' % task_type, body={'data': {}})
            data = self.parse_response(r)
            self.assertIn(task_type, data['docs'])
