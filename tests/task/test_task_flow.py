#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from controller import errors
from controller.task.base import TaskHandler
from controller.task.api import PublishTasksApi
from tornado.escape import json_encode


class TestTaskFlow(APITestCase):
    def setUp(self):
        super(TestTaskFlow, self).setUp()

        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=r[0], name=r[2], password=r[1])
                                 for r in [u.expert1, u.expert2, u.expert3]],
                                ','.join(['切分专家', '文字专家']))

        self.assert_code(200, self.fetch('/api/task/unlock/cut/'))  # 清除切分任务

    def tearDown(self):
        # 退回所有任务，还原改动
        for task_type in TaskHandler.task_types.keys():
            self.assert_code(200, self.fetch('/api/task/unlock/%s/' % task_type))

        super(TestTaskFlow, self).tearDown()

    def publish(self, task_type, data):
        return self.fetch('/api/task/publish/%s' % task_type, body={'data': data})

    def _set_page_status(self, page_names, task_type, status):
        condition = {'name': {'$in': page_names}}
        update_value = PublishTasksApi.get_status_update(task_type, status)
        self._app.db.page.update_many(condition, {'$set': update_value})

    def _test_publish_task(self, task_type):
        # pages = [
        #     'GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87', 'JX_245_1_21', 'JX_245_1_24',
        #     'QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389', 'YB_22_476', 'YB_22_555',
        #     'YB_22_713', 'YB_22_759', 'YB_22_816', 'YB_22_916', 'YB_22_995'
        # ]

        # 测试页面为空
        r = self.parse_response(self.publish(task_type, dict(pages='')))
        self.assertIsInstance(r['data'], dict)
        self.assertFalse(hasattr(r['data'], 'published'))

        # 测试不存在的页面
        pages_not_existed = ['GL_not_existed_1', 'JX_not_existed_2']
        r = self.parse_response(self.publish(task_type, dict(pages=','.join(pages_not_existed), priority='高')))
        self.assertEqual(pages_not_existed, r['data']['not_existed'])

        # 测试未就绪的页面
        pages_not_ready = ['GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87']
        self._set_page_status(pages_not_ready, task_type, TaskHandler.STATUS_UNREADY)
        r = self.parse_response(self.publish(task_type, dict(pages=','.join(pages_not_ready), priority='高')))
        self.assertEqual(pages_not_ready, r['data']['not_ready'])

        # 测试已就绪的页面
        pages_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        self._set_page_status(pages_ready, task_type, TaskHandler.STATUS_READY)
        r = self.parse_response(self.publish(task_type, dict(pages=','.join(pages_ready), priority='高')))
        status = 'pending' if TaskHandler.pre_tasks().get(task_type) else 'published'
        self.assertEqual(pages_ready, r['data'][status])
        self._set_page_status(pages_ready, task_type, TaskHandler.STATUS_READY)

        # 测试已发布的页面
        pages_published = ['YB_22_713', 'YB_22_759', 'YB_22_816', 'YB_22_916', 'YB_22_995']
        self._set_page_status(pages_published, task_type, TaskHandler.STATUS_OPENED)
        r = self.parse_response(self.publish(task_type, dict(pages=','.join(pages_published), priority='高')))
        self.assertEqual(pages_published, r['data']['published_before'])

        # 组合测试
        all_pages = pages_not_existed + pages_not_ready + pages_ready + pages_published
        self._set_page_status(pages_not_ready, task_type, TaskHandler.STATUS_UNREADY)
        self._set_page_status(pages_ready, task_type, TaskHandler.STATUS_READY)
        self._set_page_status(pages_published, task_type, TaskHandler.STATUS_OPENED)
        r = self.parse_response(self.publish(task_type, dict(pages=','.join(all_pages), priority='高')))
        self.assertEqual(pages_not_existed, r['data']['not_existed'])
        self.assertEqual(pages_not_ready, r['data']['not_ready'])
        self.assertEqual(pages_ready, r['data'][status])
        self.assertEqual(pages_published, r['data']['published_before'])

    def test_publish_tasks(self):
        """ 测试发布审校任务 """
        self.add_first_user_as_admin_then_login()
        self._test_publish_task('block_cut_proof')  # 测试一级任务
        self._test_publish_task('block_cut_review')  # 测试一级任务有前置任务的情况
        self._test_publish_task('text_proof')  # 测试一级任务有子任务的情况
        self._test_publish_task('text_proof.1')  # 测试二级任务

    def test_task_lobby(self):
        """ 测试任务大厅 """

        self.login_as_admin()
        for task_type in ['block_cut_proof', 'column_cut_proof', 'char_cut_proof', 'block_cut_review',
                          'column_cut_review', 'char_cut_review', 'text_proof', 'text_review']:
            if task_type == 'text_proof':
                for i in range(1, 4):
                    r = self.parse_response(self.publish('%s.%d' % (task_type, i),
                                                         dict(pages='GL_1056_5_6,JX_165_7_12')))
            else:
                r = self.parse_response(self.publish(task_type, dict(pages='GL_1056_5_6,JX_165_7_12')))
            self.assertEqual({'opened'}, set([t['status'] for t in r['data']]), msg=task_type)

            r = self.fetch('/task/lobby/%s?_raw=1&_no_auth=1' % task_type)
            self.assert_code(200, r, msg=task_type)
            r = self.parse_response(r)
            self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set([t['name'] for t in r['tasks']]), msg=task_type)
            self.assert_code(200, self.fetch('/api/task/unlock/cut/'))
            self.assert_code(200, self.fetch('/api/task/unlock/text/'))

    def test_cut_proof(self):
        """ 测试切分校对的任务领取、保存和提交 """

        for task_type in TaskHandler.cut_task_names:
            # 发布任务
            self.login_as_admin()
            self.assert_code(200, self.fetch('/api/task/unlock/cut/'))
            self.assert_code(200, self.publish(task_type, dict(pages='GL_1056_5_6,JX_165_7_12')))

            # 任务大厅
            self.login(u.expert1[0], u.expert1[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            tasks = r.get('tasks')
            self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set([t['name'] for t in tasks]), msg=task_type)

            # 领取任务
            r = self.parse_response(self.fetch(tasks[0]['pick_url'] + '?_raw=1'))
            page = r.get('page')
            self.assertIn(task_type, page)
            self.assertEqual(page[task_type]['status'], 'picked')
            self.assertEqual(page[task_type]['picked_by'], u.expert1[2])

            # 再领取新任务就提示有未完成任务
            r = self.parse_response(self.fetch(tasks[1]['pick_url'] + '?_raw=1'))
            self.assertIn('links', r)
            r = self.parse_response(self.fetch(tasks[1]['pick_url']))
            self.assertIn('继续任务</a>', r)

            # 其他人不能领取此任务
            self.login(u.expert2[0], u.expert2[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            self.assertNotIn(page['name'], [t['name'] for t in r.get('tasks')])
            r = self.fetch('/task/do/%s/%s?_raw=1' % (task_type, page['name']))
            self.assert_code(errors.task_locked, r)

            # 保存
            self.login(u.expert1[0], u.expert1[1])
            box_type = task_type.split('_')[0]
            boxes = page[box_type + 's']
            r = self.fetch('/api/task/save/%s?_raw=1' % (task_type,),
                           body={'data': dict(name=page['name'], box_type=box_type, boxes=json_encode(boxes))})
            self.assert_code(200, r)
            self.assertFalse(self.parse_response(r).get('box_changed'))

            boxes[0]['w'] += 1
            r = self.fetch('/api/task/save/%s?_raw=1' % (task_type,),
                           body={'data': dict(name=page['name'], box_type=box_type, boxes=json_encode(boxes))})
            self.assertTrue(self.parse_response(r).get('box_changed'))

            # 提交
            boxes[0]['w'] -= 1
            r = self.fetch('/api/task/save/%s?_raw=1' % (task_type,),
                           body={'data': dict(name=page['name'], submit=True,
                                              box_type=box_type, boxes=json_encode(boxes))})
            self.assert_code(200, r)
            self.assertTrue(self.parse_response(r).get('submitted'))

    def test_cut_relation(self):
        """ 测试切分审校的前后依赖关系 """

        # 发布两个栏切分审校任务
        self.login_as_admin()
        self.assert_code(200, self.publish('block_cut_proof', dict(pages='GL_1056_5_6,JX_165_7_12')))
        tasks = self.parse_response(self.fetch('/task/lobby/block_cut_proof?_raw=1'))['tasks']
        self.assert_code(200, self.publish('block_cut_review', dict(pages='GL_1056_5_6,JX_165_7_12')))

        # 领取并提交
        self.login(u.expert1[0], u.expert1[1])
        page = self.parse_response(self.fetch(tasks[0]['pick_url'] + '?_raw=1'))['page']
        self.assertIn('name', page)
        r = self.fetch('/api/task/save/block_cut_proof?_raw=1',
                       body={'data': dict(name=page['name'], submit=True,
                                          box_type='block', boxes=json_encode(page['blocks']))})
        r = self.parse_response(r)
        self.assertRegex(r.get('jump'), r'^/task/do/')
        self.assertIn(tasks[1]['name'], r.get('jump'))
        self.assertEqual(r.get('resume_next'), 'block_cut_review')
