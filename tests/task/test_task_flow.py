#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase
from controller import errors
from controller.task.base import TaskHandler as th
from tornado.escape import json_encode


class TestTaskFlow(APITestCase):
    pre_tasks = {
        'block_cut_proof': None,
        'block_cut_review': 'block_cut_proof',
        'column_cut_proof': None,
        'column_cut_review': 'column_cut_proof',
        'char_cut_proof': None,
        'char_cut_review': 'char_cut_proof',
        'text_proof_1': None,
        'text_proof_2': None,
        'text_proof_3': None,
        'text_review': ['text_proof_1', 'text_proof_2', 'text_proof_3'],
    }

    def setUp(self):
        super(TestTaskFlow, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        self._revert()

    def tearDown(self):
        super(TestTaskFlow, self).tearDown()

    def _revert(self, status=th.STATUS_READY):
        """ 还原所有任务的状态 """
        pages = self._app.db.page.find()
        for page in pages:
            update = dict(tasks={}, lock={})
            for task_key, v in page.get('tasks').items():
                update['tasks'][task_key] = dict(status=status)
            for lock_key, v in page.get('lock').items():
                update['lock'][lock_key] = dict()
            self._app.db.page.update_one({'name': page['name']}, {'$set': update})

    def _publish(self, data):
        if 'task_type' in data and 'pre_tasks' not in data:
            data['pre_tasks'] = self.pre_tasks.get(data['task_type'])
        return self.fetch('/api/task/publish', body={'data': data})

    def _set_page_status(self, page_names, task_type_status_dict):
        update_value = dict()
        for task_type, status in task_type_status_dict.items():
            update_value.update({'tasks.%s.status' % task_type: status})
        self._app.db.page.update_many({'name': {'$in': page_names}}, {'$set': update_value})

    def test_task_lobby(self):
        """ 测试任务大厅 """

        self.login_as_admin()
        for task_type in self.pre_tasks.keys():
            page_names = ['GL_1056_5_6', 'JX_165_7_12']
            self._set_page_status(page_names, {task_type: 'ready'})
            r = self.parse_response(self._publish(
                dict(task_type=task_type, pages=','.join(page_names))))
            published = r.get('data', {}).get('published')
            pending = r.get('data', {}).get('pending')
            if 'proof' in task_type:
                self.assertIsInstance(published, list, msg=task_type)
                self.assertEqual(set(page_names), set(published), msg=task_type)
            elif 'review' in task_type:
                self.assertIsInstance(pending, list, msg=task_type)
                self.assertEqual(set(page_names), set(pending), msg=task_type)
            lobby_type = 'text_proof' if 'text_proof' in task_type else task_type
            r = self.fetch('/task/lobby/%s?_raw=1&_no_auth=1' % lobby_type)
            self.assert_code(200, r, msg=task_type)
            r = self.parse_response(r)
            if published:
                self.assertEqual(set(page_names), set([t['name'] for t in r['tasks']]), msg=task_type)

    def test_cut_proof(self):
        """ 测试切分校对的任务领取、保存和提交和前后置任务关系 """
        for task_type in [
            'block_cut_proof', 'block_cut_review',
            'column_cut_proof', 'column_cut_review',
            'char_cut_proof', 'char_cut_review'
        ]:
            self.login_as_admin()
            # 发布任务
            page_names = ['GL_1056_5_6', 'JX_165_7_12']
            self.assert_code(200, self._publish(dict(
                task_type=task_type, pages=','.join(page_names))))

            # 任务大厅
            self.login(u.expert1[0], u.expert1[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            tasks = r.get('tasks')
            if 'review' in task_type:
                self.assertIn(page_names[0], [t['name'] for t in tasks], msg=task_type)
            else:
                self.assertEqual(set(page_names), set([t['name'] for t in tasks]), msg=task_type)

            # 领取第一个页面
            url = '/api/task/pick/' + task_type
            r = self.parse_response(self.fetch(url, body={'data': {'page_name': page_names[0]}}))
            self.assertEqual(page_names[0], r.get('page_name'), msg=task_type)
            page = self._app.db.page.find_one({'name': page_names[0]})
            self.assertIn(task_type, page['tasks'])
            self.assertEqual(page['tasks'][task_type]['status'], 'picked')
            self.assertEqual(page['tasks'][task_type]['picked_by'], u.expert1[2])

            # 再领取新任务时，提示有未完成任务
            r = self.parse_response(self.fetch(url, body={}))
            self.assertEqual(errors.task_uncompleted[0], r.get('code'))

            # 其他人不能领取此任务
            self.login(u.expert2[0], u.expert2[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % task_type))
            self.assertNotIn(page['name'], [t['name'] for t in r.get('tasks')])
            r = self.fetch('/task/do/%s/%s?_raw=1' % (task_type, page['name']))
            self.assert_code(errors.task_unauthorized, r)

            # 保存任务
            self.login(u.expert1[0], u.expert1[1])
            box_type = task_type.split('_')[0]
            boxes = page[box_type + 's']
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (task_type, page['name']),
                body={'data': dict(box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assert_code(200, r)
            self.assertTrue(self.parse_response(r).get('updated'))

            # 提交任务，保证review有任务可领取
            boxes[0]['w'] -= 1
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (task_type, page['name']),
                body={'data': dict(submit=True, box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assert_code(200, r)
            self.assertTrue(self.parse_response(r).get('submitted'))

            if 'proof' in task_type:
                # 领取第二个任务
                url = '/api/task/pick/' + task_type
                r = self.parse_response(self.fetch(url, body={}))
                page = self._app.db.page.find_one({'name': r.get('page_name')})
                self.assertIn(task_type, page['tasks'])
                self.assertEqual(page['tasks'][task_type]['status'], 'picked')
                self.assertEqual(page['tasks'][task_type]['picked_by'], u.expert1[2])

                # 退回第二个任务
                url = '/api/task/return/%s/%s' % (task_type, page['name'])
                r = self.parse_response(self.fetch(url, body={}))
                self.assertTrue(r.get('returned'))

    def test_cut_relation(self):
        """ 测试切分审校的前后依赖关系 """
        cut_pre_tasks = {
            'block_cut_review': 'block_cut_proof',
            'column_cut_review': 'column_cut_proof',
            'char_cut_review': 'char_cut_proof',
        }

        for t1, t2 in cut_pre_tasks.items():
            # 发布t2，领取t2并提交
            self.login_as_admin()
            page_names = ['GL_1056_5_6', 'JX_165_7_12']
            r = self._publish(dict(task_type=t2, pre_tasks=self.pre_tasks.get(t2), pages=','.join(page_names)))
            self.assert_code(200, r)
            self.login(u.expert1[0], u.expert1[1])
            self.parse_response(self.fetch('/api/task/pick/' + t2, body={'data': {'page_name': page_names[0]}}))
            page = self._app.db.page.find_one({'name': page_names[0]})
            box_type = t2.split('_')[0]
            boxes = page[box_type + 's']
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (t2, page['name']),
                body={'data': dict(submit=True, box_type=box_type, boxes=json_encode(boxes))}
            )
            self.assertTrue(self.parse_response(r).get('submitted'))

            # 发布t1，任务大厅应有任务
            self.login_as_admin()
            r = self._publish(dict(task_type=t1, pre_tasks=self.pre_tasks.get(t1), pages=','.join(page_names)))
            self.assert_code(200, r)
            self.login(u.expert1[0], u.expert1[1])
            r = self.parse_response(self.fetch('/task/lobby/%s?_raw=1' % t1))
            self.assertIn(page_names[0], [t['name'] for t in r.get('tasks')], msg=t1)

    def test_text_proof_task(self):
        """ 测试文字校对任务的领取和提交 """

        # 发布一个页面的校一、校二、校三任务
        self.login_as_admin()
        page_name = 'GL_1056_5_6'
        for t in ['text_proof_1', 'text_proof_2', 'text_proof_3']:
            r = self._publish(dict(task_type=t, pre_tasks=self.pre_tasks.get(t), pages=page_name))
            r = self.parse_response(r)
            self.assertEqual(r.get('published'), ['GL_1056_5_6'])

        # 领取一个任务
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/text_proof_1', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 不能领取同一页面的其它校次任务
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': page_name}})
        self.assert_code(errors.task_text_proof_duplicated, r)

        # 完成任务
        page = self._app.db.page.find_one({'name': page_name})
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % page_name,
            body={'data': dict(submit=True, txt1=json_encode(page['ocr']))}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 已完成的任务，不可以do
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % page_name,
            body={'data': dict(submit=True, txt1=json_encode(page['ocr']))}
        )
        self.assert_code(errors.task_finished_not_allowed_do, r)

        # 已完成的任务，可以update进行编辑，完成时间不变
        finished_time1 = page['tasks']['text_proof_1'].get('finished_time')
        r = self.fetch(
            '/api/task/update/text_proof_1/%s?_raw=1' % page_name,
            body={'data': dict(submit=True, txt1=json_encode(page['ocr']))}
        )
        self.assertTrue(self.parse_response(r).get('updated'))
        finished_time2 = page['tasks']['text_proof_1'].get('finished_time')
        self.assertEqual(finished_time1, finished_time2)

    def test_text_returned_then_pick(self):
        """ 测试先退回文字校对任务，再领取同一页面其它校次的文字校对任务 """

        # 发布两个校次的文字校对任务
        self.login_as_admin()
        self.fetch('/api/task/unlock/text_proof/')
        self.assert_code(200, self._publish(dict(task_type='text_proof_1', pages='GL_1056_5_6,JX_165_7_12')))
        self.assert_code(200, self._publish(dict(task_type='text_proof_2', pages='GL_1056_5_6')))

        # 领取一个任务
        self.login(u.expert1[0], u.expert1[1])
        self.assert_code(200, self.fetch('/api/task/pick/text_proof_1', body={'data': {'page_name': 'GL_1056_5_6'}}))

        # 退回任务
        r = self.parse_response(self.fetch('/api/task/return/text_proof_1/GL_1056_5_6', body={}))
        self.assertTrue(r.get('returned'))

        # 领取其它校次任务
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': 'GL_1056_5_6'}})
        self.assert_code(errors.task_text_proof_duplicated, r)

    def test_lobby_order(self):
        """测试任务大厅的任务显示顺序"""
        self.login_as_admin()
        self._publish(dict(task_type='text_proof_1', pages='GL_1056_5_6', priority=2))
        self._publish(dict(task_type='text_proof_1', pages='JX_165_7_12', priority=3))
        self._publish(dict(task_type='text_proof_2', pages='JX_165_7_12', priority=2))
        self._publish(dict(task_type='text_proof_3', pages='JX_165_7_12', priority=1))
        self._publish(dict(task_type='text_proof_2', pages='JX_165_7_30', priority=1))

        self.login(u.expert1[0], u.expert1[1])
        for i in range(5):
            r = self.parse_response(self.fetch('/task/lobby/text_proof?_raw=1'))
            names = [t['name'] for t in r.get('tasks', [])]
            self.assertEqual(set(names), {'GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30'})
            self.assertEqual(len(names), len(set(names)))  # 不同校次的同名页面只列出一个
            self.assertEqual(names, ['JX_165_7_12', 'GL_1056_5_6', 'JX_165_7_30'])  # 按优先级顺序排列
