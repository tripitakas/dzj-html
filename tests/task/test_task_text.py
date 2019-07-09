#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase


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

    def test_view_text_proof(self):
        # 测试查看校对任务
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

    def test_api_get_cmp(self):
        """ 测试获取比对文本 """
        page_name = 'JX_165_7_75'
        self.login(u.expert1[0], u.expert1[1])

        # 测试获取比对本
        r = self.parse_response(
            self.fetch('/api/task/text_proof/get_cmp/%s' % page_name, body={'data': {'num': 1}}))
        self.assertTrue(r.get('cmp'))
        self.assertTrue(r.get('hit_page_codes'))

        # 测试获取上一页文本
        data = {'data': {'cmp_page_code': r.get('hit_page_codes')[0], 'neighbor': 'prev'}}
        r = self.parse_response(self.fetch('/api/task/text_proof/get_cmp_neighbor', body=data))
        self.assertTrue(r.get('txt'))

    def test_view_find_cmp(self):
        """ 测试选择比对文本 """
        # 发布一个页面
        page_name = 'GL_1056_5_6'
        task_type = 'text_proof_1'
        self.login_as_admin()
        r = self.publish(dict(task_type=task_type, pre_tasks=self.pre_tasks.get(task_type), pages=page_name))
        r = self.parse_response(r)
        self.assertEqual(r.get('published'), ['GL_1056_5_6'])

        # 领取校一
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/%s' % task_type, body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 进入选择比对文本页面
        r = self.fetch('/task/do/%s/find_cmp/%s?_raw=1' % (task_type, page_name))
        self.assert_code(200, r)

        # 提交任务
        r = self.fetch(
            '/api/task/do/%s/find_cmp/%s?_raw=1' % (task_type, page_name),
            body={'data': dict(submit_step=True)}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 进入文字校对页面
        r = self.fetch('/task/do/%s/%s?_raw=1' % (task_type, page_name))
        self.assert_code(200, r)

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
        r = self.fetch('/api/task/do/text_proof_1/%s?_raw=1' % page_name, body={'data': dict(submit=True)})
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取校二
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成校二
        r = self.fetch('/api/task/do/text_proof_2/%s?_raw=1' % page_name, body={'data': dict(submit=True)})
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取校三
        self.login(u.expert3[0], u.expert3[1])
        r = self.fetch('/api/task/pick/text_proof_3', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成校三
        r = self.fetch('/api/task/do/text_proof_3/%s?_raw=1' % page_name, body={'data': dict(submit=True)})
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取审定
        r = self.fetch('/api/task/pick/text_review', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

        # 完成审定
        doubt = "<tr class='char-list-tr' data='line-8' data-offset='10' data-reason='理由1'>" \
                "<td>8</td><td>10</td><td>存疑内容一</td><td>理由1</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>" \
                "<tr class='char-list-tr' data='line-3' data-offset='6' data-reason='理由2'>" \
                "<td>3</td><td>6</td><td>存疑内容二</td><td>理由2</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>"
        r = self.fetch('/api/task/do/text_review/%s?_raw=1' % page_name, body={'data': dict(submit=True, doubt=doubt)})
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 领取难字任务
        r = self.fetch('/api/task/pick/text_hard', body={'data': {'page_name': page_name}})
        self.assert_code(200, r)

