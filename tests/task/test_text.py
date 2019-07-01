#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from controller import errors
from tests.testcase import APITestCase
from tornado.escape import json_encode


class TestText(APITestCase):
    def setUp(self):
        super(TestText, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        self.revert()

    def tearDown(self):
        super(TestText, self).tearDown()

    def test_text_view(self):
        # 发布一个页面的校一、校二、校三任务
        self.login_as_admin()
        page_name = 'GL_1056_5_6'
        for t in ['text_proof_1', 'text_proof_2', 'text_proof_3']:
            r = self.publish(dict(task_type=t, pre_tasks=self.pre_tasks.get(t), pages=page_name))
            r = self.parse_response(r)
            self.assertEqual(r.get('published'), ['GL_1056_5_6'])
            # 查看校对页面
            r = self.fetch('/task/%s/GL_924_2_35?_raw=1' % t)
            self.assert_code(200, r)
            r = self.parse_response(r)
            self.assertIn('cmp_data', r)
            self.assertEqual(r.get('readonly'), True)

    def test_text_submit(self):
        # 发布一个页面的校一、校二、校三任务
        self.login_as_admin()
        page_name = 'GL_1056_5_6'
        for t in ['text_proof_1', 'text_proof_2', 'text_proof_3']:
            r = self.parse_response(self.publish(dict(task_type=t, pre_tasks=self.pre_tasks.get(t), pages=page_name)))
            self.assertEqual(r.get('published'), ['GL_1056_5_6'])

        # 发布审定任务
        r = self.parse_response(
            self.publish(dict(task_type='text_review', pre_tasks=self.pre_tasks.get('text_review'), pages=page_name)))
        self.assertEqual(r.get('pending'), ['GL_1056_5_6'])

        # 领取校一
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/text_proof_1', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成校一
        page = self._app.db.page.find_one({'name': page_name})
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % page_name,
            body={'data': dict(submit=True)}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取校二
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成校二
        page = self._app.db.page.find_one({'name': page_name})
        r = self.fetch(
            '/api/task/do/text_proof_2/%s?_raw=1' % page_name,
            body={'data': dict(submit=True)}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取校三
        self.login(u.expert3[0], u.expert3[1])
        r = self.fetch('/api/task/pick/text_proof_3', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成校三
        page = self._app.db.page.find_one({'name': page_name})
        r = self.fetch(
            '/api/task/do/text_proof_3/%s?_raw=1' % page_name,
            body={'data': dict(submit=True)}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取审定
        r = self.fetch('/api/task/pick/text_review', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成审定
        page = self._app.db.page.find_one({'name': page_name})
        r = self.fetch(
            '/api/task/do/text_review/%s?_raw=1' % page_name,
            body={'data': dict(submit=True)}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))
