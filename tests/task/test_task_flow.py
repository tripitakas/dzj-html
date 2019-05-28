#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime, date
import tests.users as u
from tests.testcase import APITestCase
from controller import errors
from controller.task.base import TaskHandler
from controller.task.api_admin import PublishTasksApi
from tornado.escape import json_encode


class TestTaskFlow(APITestCase):
    def setUp(self):
        super(TestTaskFlow, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )

    def tearDown(self):
        # 退回所有任务，还原改动
        for task_type in TaskHandler.task_types.keys():
            self.assert_code(200, self.fetch('/api/task/unlock/%s/' % task_type))
        for i in range(1, 4):
            self.assert_code(200, self.fetch('/api/task/unlock/text_proof.%d/' % i))
        super(TestTaskFlow, self).tearDown()

    def publish(self, data):
        return self.fetch('/api/task/publish', body={'data': data})

    def _set_page_status(self, page_names, task_type_status_dict):
        update_value = dict()
        for task_type, status in task_type_status_dict.items():
            update_value.update(PublishTasksApi.get_status_update(task_type, status))
        self._app.db.page.update_many({'name': {'$in': page_names}}, {'$set': update_value})

    def _assert_response(self, pages, response, task_type_status_dict):
        for task_type, status in task_type_status_dict.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages))

    def _test_publish_many_tasks(self, task_type, size):
        pages = self._app.db.page.find({}, {'name': 1}).limit(size)
        page_names = [page['name'] for page in pages]
        self._set_page_status(page_names, {task_type: TaskHandler.STATUS_READY})
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(page_names))))
        status = 'pending' if TaskHandler.pre_tasks().get(task_type) else 'published'
        self.assertIn(status, r['data'])

    def _test_publish_task(self, task_type):
        task_type = [task_type] if isinstance(task_type, str) else task_type
        # 测试不存在的页面
        pages_un_existed = ['GL_not_existed_1', 'JX_not_existed_2']
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_un_existed))))
        self._assert_response(pages_un_existed, r, {t: 'un_existed' for t in task_type})

        # 测试未就绪的页面
        pages_un_ready = ['GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87']
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_UNREADY for t in task_type})
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_un_ready))))
        self._assert_response(pages_un_ready, r, {t: 'un_ready' for t in task_type})

        # 测试已就绪的页面
        pages_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_ready))))
        pre_tasks = TaskHandler.pre_tasks()
        self._assert_response(pages_ready, r, {t: 'pending' if pre_tasks.get(t) else 'published' for t in task_type})
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})

        # 测试已发布的页面
        pages_published_before = ['YB_22_713', 'YB_22_759', 'YB_22_816', 'YB_22_916', 'YB_22_995']
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_OPENED for t in task_type})
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(pages_published_before))))
        self._assert_response(pages_published_before, r, {t: 'published_before' for t in task_type})

        # 组合测试
        all_pages = pages_un_existed + pages_un_ready + pages_ready + pages_published_before
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_UNREADY for t in task_type})
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_OPENED for t in task_type})
        r = self.parse_response(self.publish(dict(task_type=task_type, pages=','.join(all_pages))))
        self._assert_response(pages_un_existed, r, {t: 'un_existed' for t in task_type})
        self._assert_response(pages_un_ready, r, {t: 'un_ready' for t in task_type})
        self._assert_response(pages_ready, r, {t: 'pending' if pre_tasks.get(t) else 'published' for t in task_type})
        self._assert_response(pages_published_before, r, {t: 'published_before' for t in task_type})

        # 还原页面状态
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_READY for t in task_type})

    def test_publish_tasks(self):
        """ 测试发布审校任务 """
        self.add_first_user_as_admin_then_login()
        # 测试异常情况
        r = self.parse_response(self.publish(dict(task_type='block_cut_proof', pages='')))  # 页面为空
        self.assertIn('pages', r['error'])

        pages = 'GL_1056_5_6,JX_165_7_12'
        r = self.parse_response(self.publish(dict(task_type='text_proof', pages=pages)))  # 任务类型有误
        self.assertIn('task_type', r['error'])

        # 优先级有误，必须为1/2/3
        r = self.parse_response(self.publish(dict(task_type='block_cut_proof', pages=pages, priority='高')))
        self.assertIn('priority', r['error'])

        # 测试正常情况
        self._test_publish_task('block_cut_proof')  # 测试一级任务
        self._test_publish_task('block_cut_review')  # 测试一级任务有前置任务的情况
        self._test_publish_task('text_proof.1')  # 测试二级任务
        self._test_publish_task(['text_proof.1', 'text_proof.2', 'text_proof.3'])  # 测试任务组合

        # 测试超大规模
        # self._test_publish_many_tasks('block_cut_proof', 10000)

    def test_task_lobby(self):
        """ 测试任务大厅 """

        self.login_as_admin()
        for task_type in [
            'block_cut_proof', 'column_cut_proof', 'char_cut_proof', 'block_cut_review', 'column_cut_review',
            'char_cut_review', 'text_review', ['text_proof.1', 'text_proof.2', 'text_proof.3']
        ]:
            r = self.parse_response(self.publish(dict(task_type=task_type, pages='GL_1056_5_6,JX_165_7_12')))
            published = r.get('data', {}).get('published')
            pending = r.get('data', {}).get('pending')
            if 'cut_proof' in task_type:
                self.assertIsInstance(published, list, msg=task_type)
                self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set(published), msg=task_type)
            elif 'cut_review' in task_type:
                self.assertIsInstance(pending, list, msg=task_type)
                self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set(pending), msg=task_type)

            r = self.fetch('/task/lobby/%s?_raw=1&_no_auth=1' % (
                task_type if isinstance(task_type, str) else 'text_proof'))
            self.assert_code(200, r, msg=task_type)
            r = self.parse_response(r)
            if published:
                self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set([t['name'] for t in r['tasks']]), msg=task_type)

            self.assert_code(200, self.fetch('/api/task/unlock/cut/'))
            self.assert_code(200, self.fetch('/api/task/unlock/text/'))

    def test_cut_proof(self):
        """ 测试切分校对的任务领取、保存和提交 """

        for task_type in TaskHandler.cut_task_names:
            # 发布任务
            self.login_as_admin()
            self.assert_code(200, self.fetch('/api/task/unlock/cut/'))
            self.assert_code(200, self.publish(dict(task_type=task_type, pages='GL_1056_5_6,JX_165_7_12')))

            # 任务大厅
            self.login(u.expert1[0], u.expert1[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            tasks = r.get('tasks')
            if 'cut_review' in task_type:
                self.assertEqual(tasks, [], msg=task_type)
                continue
            self.assertEqual({'GL_1056_5_6', 'JX_165_7_12'}, set([t['name'] for t in tasks]), msg=task_type)

            # 领取任务
            r = self.parse_response(self.fetch('/api%s' % tasks[0]['pick_url']))
            self.assertIn('url', r)
            r = self.parse_response(self.fetch('%s?_raw=1' % r['url']))
            page = r.get('page')
            self.assertIn(task_type, page)
            self.assertEqual(page[task_type]['status'], 'picked')
            self.assertEqual(page[task_type]['picked_by'], u.expert1[2])

            # 再领取新任务就提示有未完成任务
            r = self.parse_response(self.fetch('/api%s' % tasks[1]['pick_url']))
            self.assertEqual(errors.task_uncompleted[0], r.get('code'))

            # 其他人不能领取此任务
            self.login(u.expert2[0], u.expert2[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            self.assertNotIn(page['name'], [t['name'] for t in r.get('tasks')])
            r = self.fetch('/task/do/%s/%s?_raw=1' % (task_type, page['name']))
            self.assert_code(errors.task_picked, r)

            # 保存
            self.login(u.expert1[0], u.expert1[1])
            box_type = task_type.split('_')[0]
            boxes = page[box_type + 's']
            r = self.fetch(
                '/api/task/save/%s?_raw=1' % (task_type,),
                body={'data': dict(name=page['name'], box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assert_code(200, r)
            self.assertFalse(self.parse_response(r).get('box_changed'))

            boxes[0]['w'] += 1
            r = self.fetch(
                '/api/task/save/%s?_raw=1' % (task_type,),
                body={'data': dict(name=page['name'], box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assertTrue(self.parse_response(r).get('box_changed'))

            # 提交
            boxes[0]['w'] -= 1
            r = self.fetch(
                '/api/task/save/%s?_raw=1' % (task_type,),
                body={'data': dict(name=page['name'], submit=True, box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assert_code(200, r)
            self.assertTrue(self.parse_response(r).get('submitted'))

    def test_cut_relation(self):
        """ 测试切分审校的前后依赖关系 """

        # 发布两个栏切分审校任务
        self.login_as_admin()
        self.assert_code(200, self.publish(dict(task_type='block_cut_proof', pages='GL_1056_5_6,JX_165_7_12')))
        tasks = self.parse_response(self.fetch('/task/lobby/block_cut_proof?_raw=1'))['tasks']
        self.assert_code(200, self.publish(dict(task_type='block_cut_review', pages='GL_1056_5_6,JX_165_7_12')))

        # 领取并提交
        self.login(u.expert1[0], u.expert1[1])
        r = self.parse_response(self.fetch('/api%s' % tasks[0]['pick_url']))
        self.assertIn('url', r, str(r))
        r = self.parse_response(self.fetch('%s?_raw=1' % r['url']))
        page = r['page']
        self.assertIn('name', page)
        r = self.fetch(
            '/api/task/save/block_cut_proof?_raw=1',
            body={'data': dict(name=page['name'], submit=True, box_type='block', boxes=json_encode(page['blocks']))}
        )
        r = self.parse_response(r)
        self.assertRegex(r.get('jump'), r'^/task/do/')
        self.assertIn(tasks[1]['name'], r.get('jump'))
        self.assertEqual(r.get('resume_next'), 'block_cut_review')

    def test_pick_text_proof_task(self):
        """ 测试文字校对任务的领取和提交 """

        # 发布一个页面的校一、校二任务
        self.login_as_admin()
        self.fetch('/api/task/unlock/text_proof/')
        r = self.parse_response(self.publish(dict(task_type=['text_proof.1', 'text_proof.2'], pages='GL_1056_5_6')))
        self.assertEqual(r.get('text_proof.1').get('published'), ['GL_1056_5_6'])
        self.assertEqual(r.get('text_proof.2').get('published'), ['GL_1056_5_6'])

        # 多次领取的是同一个任务
        self.login(u.expert1[0], u.expert1[1])
        self.assert_code(200, self.fetch('/api/task/pick/text_proof.1/GL_1056_5_6'))
        r1 = self.fetch('/api/task/pick/text_proof/GL_1056_5_6')
        self.assert_code(200, r1)
        r2 = self.fetch('/api/task/pick/text_proof/GL_1056_5_6')
        self.assert_code(200, r2)
        r1, r2 = self.parse_response(r1), self.parse_response(r2)
        self.assertEqual(r1['url'], r2['url'])

        # 让此任务完成
        r = self.parse_response(self.fetch('%s?_raw=1' % r1['url']))
        page = r.get('page')
        self.assertIn('name', page)
        r = self.fetch(
            '/api/task/save/text_proof/%s?_raw=1' % r1['url'].split('/')[-2],
            body={'data': dict(name=page['name'], submit=True, chars=json_encode(page['chars']))}
        )
        self.assert_code(200, r)
        # 页面相同，不能再自动领另一个校次的
        self.assertFalse(self.parse_response(r).get('jump'))

        # 已完成的任务还可以再次继续编辑，任务状态不变
        r = self.parse_response(self.fetch('%s?_raw=1' % r1['url']))
        p2 = r.get('page') or {}
        self.assertEqual(p2.get('name'), page['name'])

        p = self.parse_response(self.fetch('/api/task/page/' + page['name']))
        self.assertEqual(TaskHandler.get_obj_property(p, r['task_type'] + '.status'), TaskHandler.STATUS_FINISHED)

    def test_text_returned_pick(self):
        """测试先退回文字校对任务再领取同一页面的文字校对任务"""

        # 发布两个校次的文字校对任务
        self.login_as_admin()
        self.fetch('/api/task/unlock/text_proof/')
        self.assert_code(200, self.publish(dict(task_type='text_proof.1', pages='GL_1056_5_6,JX_165_7_12')))
        self.assert_code(200, self.publish(dict(task_type='text_proof.2', pages='GL_1056_5_6')))

        # 领取一个任务
        self.login(u.expert1[0], u.expert1[1])
        self.assert_code(200, self.fetch('/api/task/pick/text_proof.1/GL_1056_5_6'))
        p = self.parse_response(self.fetch('/api/task/page/GL_1056_5_6'))
        self.assertEqual(TaskHandler.get_obj_property(p, 'text_proof.1.status'), TaskHandler.STATUS_PICKED)

        # 再领取相同任务则结果不变
        r = self.parse_response(self.fetch('/api/task/pick/text_proof.1/GL_1056_5_6'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/1/GL_1056_5_6')

        # 再领取别的任务则结果不变
        r = self.parse_response(self.fetch('/api/task/pick/text_proof.2/GL_1056_5_6'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/1/GL_1056_5_6')
        r = self.parse_response(self.fetch('/api/task/pick/text_proof.1/JX_165_7_12'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/1/GL_1056_5_6')
        r = self.parse_response(self.fetch('/api/task/pick/text_proof/GL_1056_5_6'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/1/GL_1056_5_6')

        # 退回任务后领取相同页面的其他校次任务

        self.assert_code(200, self.fetch('/api/task/unlock/text_proof.1/GL_1056_5_6'))
        p = self.parse_response(self.fetch('/api/task/page/GL_1056_5_6'))
        self.assertEqual(TaskHandler.get_obj_property(p, 'text_proof.1.status'), TaskHandler.STATUS_READY)
        self.assertIsNone(TaskHandler.get_obj_property(p, 'text_proof.1.picked_user_id'))
        self.assertIsNone(TaskHandler.get_obj_property(p, 'text_proof.1.picked_by'))

        r = self.parse_response(self.fetch('/api/task/pick/text_proof.2/GL_1056_5_6'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/2/GL_1056_5_6')

        self.assert_code(200, self.fetch('/api/task/unlock/text_proof.2/GL_1056_5_6', body={}))
        p = self.parse_response(self.fetch('/api/task/page/GL_1056_5_6'))
        self.assertEqual(TaskHandler.get_obj_property(p, 'text_proof.2.status'), TaskHandler.STATUS_RETURNED)
        self.assertIsNone(TaskHandler.get_obj_property(p, 'text_proof.2.picked_user_id'))
        self.assertTrue(TaskHandler.get_obj_property(p, 'text_proof.2.picked_by'))

        r = self.parse_response(self.fetch('/api/task/pick/text_proof.2/GL_1056_5_6'))
        self.assertEqual(r.get('url'), '/task/do/text_proof/2/GL_1056_5_6')

        p = self.parse_response(self.fetch('/api/task/page/GL_1056_5_6'))
        self.assertEqual(TaskHandler.get_obj_property(p, 'text_proof.2.status'), TaskHandler.STATUS_PICKED)

    def test_lobby_order(self):
        """测试任务大厅的任务显示顺序"""
        self.login_as_admin()
        self.fetch('/api/task/unlock/text_proof/')
        self.publish(dict(task_type='text_proof.1', pages='GL_1056_5_6', priority=2))
        self.publish(dict(task_type='text_proof.2', pages='JX_165_7_12', priority=1))
        self.publish(dict(task_type='text_proof.2', pages='JX_165_7_30', priority=2))
        self.publish(dict(task_type='text_proof.3', pages='JX_165_7_12', priority=1))

        self.login(u.expert1[0], u.expert1[1])
        for i in range(5):
            r = self.parse_response(self.fetch('/task/lobby/text_proof?_raw=1'))
            names = [t['name'] for t in r.get('tasks', [])]
            self.assertEqual(set(names), {'GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30'})
            self.assertEqual(names[0], 'JX_165_7_12')
