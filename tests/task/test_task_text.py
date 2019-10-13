#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from controller import errors
from tests.testcase import APITestCase
from tornado.escape import json_encode


class TestText(APITestCase):
    def setUp(self):
        super(TestText, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3, u.expert3]],
            '切分专家,文字专家'
        )
        self.delete_all_tasks()

    def tearDown(self):
        super(TestText, self).tearDown()

    def test_text_flow(self):
        """ 测试文字校对流程 """
        page_names = ['GL_1056_5_6', 'JX_165_7_12']
        name1 = page_names[0]
        name2 = page_names[1]
        users = [u.expert1, u.expert2, u.expert3, u.expert4]
        for i, task_type in enumerate(['text_proof_1', 'text_proof_2', 'text_proof_3']):
            # 发布任务
            self.login_as_admin()
            r = self.publish_tasks(dict(task_type=task_type, pages=','.join(page_names)))
            self.assertListEqual(self.parse_response(r).get('published'), page_names)

            # 领取任务
            self.login(users[i][0], users[i][1])
            r = self.fetch('/api/task/pick/%s' % task_type, body={'data': {'page_name': name1}})
            self.assert_code(200, r)

            # 第一步：选择比对文本
            r = self.fetch('/task/do/%s/%s?step=select_compare_text&_raw=1' % (task_type, name1))
            self.assert_code(200, r)

            # 测试获取比对本
            r = self.parse_response(
                self.fetch('/api/task/text_proof/get_compare/%s' % name1, body={'data': {'num': 1}}))
            self.assertTrue(r.get('cmp'))
            self.assertTrue(r.get('hit_page_codes'))

            # 提交第一步
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (task_type, name1),
                body={'data': dict(submit=True, cmp=r.get('cmp'), step='select_compare_text')}
            )
            page = self._app.db.page.find_one({'name': name1})
            self.assertIsNotNone(page['tasks'][task_type]['steps']['submitted'])

            # 第二步：文字校对
            r = self.fetch('/task/do/%s/%s?step=proof&_raw=1' % (task_type, name1))
            self.assert_code(200, r)

            # 提交第二步
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (task_type, name1),
                body={'data': dict(submit=True, txt_html=json_encode(page.get('ocr')), step='proof')}
            )
            self.assertTrue(self.parse_response(r).get('submitted'))

        # 发布审定任务
        self.login_as_admin()
        r = self.parse_response(self.publish_tasks(dict(task_type='text_review', pages=','.join(page_names))))
        self.assertEqual(r.get('published'), [name1])
        self.assertEqual(r.get('pending'), [name2])

        # 领取文字审定
        self.login(users[3][0], users[3][1])
        r = self.fetch('/api/task/pick/text_review', body={'data': {'page_name': name1}})
        self.assert_code(200, r)

        # 完成文字审定
        doubt = "<tr class='char-list-tr' data='line-8' data-offset='10' data-reason='理由1'>" \
                "<td>8</td><td>10</td><td>存疑内容一</td><td>理由1</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>" \
                "<tr class='char-list-tr' data='line-3' data-offset='6' data-reason='理由2'>" \
                "<td>3</td><td>6</td><td>存疑内容二</td><td>理由2</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>"
        r = self.fetch('/api/task/do/text_review/%s?_raw=1' % name1, body={'data': dict(submit=True, doubt=doubt)})
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 难字审定任务大厅应有任务
        r = self.parse_response(self.fetch('/task/lobby/text_hard?_raw=1'))
        names = [t['name'] for t in r.get('tasks', [])]
        self.assertEqual(set(names), {name1})

        # 领取难字审定
        r = self.fetch('/api/task/pick/text_hard', body={'data': {'page_name': name1}})
        self.assert_code(200, r)

        # 完成难字审定
        r = self.fetch('/api/task/do/text_hard/%s?_raw=1' % name1, body={'data': dict(submit=True)})
        self.assertTrue(self.parse_response(r).get('submitted'))

    def test_text_extra_flow(self):
        """ 测试文字校对其它流程 """

        # 发布一个页面的校一、校二、校三任务
        self.login_as_admin()
        page_names = ['GL_1056_5_6', 'JX_165_7_12']
        name1 = page_names[0]
        name2 = page_names[1]
        for t in ['text_proof_1', 'text_proof_2', 'text_proof_3']:
            r = self.publish_tasks(dict(task_type=t, pre_tasks=self.pre_tasks.get(t), pages=','.join(page_names)))
            self.assertListEqual(self.parse_response(r).get('published'), page_names)
            # 查看校对页面
            r = self.parse_response(self.fetch('/task/%s/%s?_raw=1' % (t, name1)))
            self.assertIn('page', r)

        # 领取一个任务
        task_type = 'text_proof_1'
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'page_name': name1}})
        self.assert_code(200, r)

        # 其他人不能领取此任务
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'page_name': name1}})
        self.assert_code(errors.task_not_published, r, msg=task_type)

        # 再领取新任务时，提示有未完成任务
        self.login(u.expert1[0], u.expert1[1])
        r = self.parse_response(self.fetch('/api/task/pick/' + task_type, body={'data': {}}))
        self.assertEqual(errors.task_uncompleted[0], r.get('code'), msg=task_type)

        # 不能领取同一页面的其它校次任务
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': name1}})
        self.assert_code(errors.task_text_proof_duplicated, r)

        # 完成任务
        page = self._app.db.page.find_one({'name': name1})
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % name1,
            body={'data': dict(submit=True, step='select_compare_text', cmp=page['ocr'])}
        )
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % name1,
            body={'data': dict(submit=True, step='proof', txt_html=json_encode(page['ocr']))}
        )
        self.assertTrue(self.parse_response(r).get('submitted'))

        # 已完成的任务，不可以do
        r = self.fetch(
            '/api/task/do/text_proof_1/%s?_raw=1' % name1,
            body={'data': dict(submit=True, step='proof', txt_html=json_encode(page['ocr']))}
        )
        self.assert_code(errors.task_finished_not_allowed_do, r)

        # 已完成的任务，可以update进行编辑，完成时间不变
        finished_time1 = page['tasks']['text_proof_1'].get('finished_time')
        r = self.fetch(
            '/api/task/update/text_proof_1/%s?_raw=1' % name1,
            body={'data': dict(submit=True, step='proof', txt_html=json_encode(page['ocr']))}
        )
        self.assertTrue(self.parse_response(r).get('updated'))
        finished_time2 = page['tasks']['text_proof_1'].get('finished_time')
        self.assertEqual(finished_time1, finished_time2)

        # 领取第二个任务
        r = self.fetch('/api/task/pick/text_proof_1', body={'data': {'page_name': name2}})
        self.assert_code(200, r)

        # 退回任务
        r = self.fetch('/api/task/return/text_proof_1/' + name2, body={'data': {'reason': '太难'}})
        self.assertTrue(self.parse_response(r).get('returned'))

        # 退回的任务，不可以领该任务其它校次的任务
        r = self.fetch('/api/task/pick/text_proof_2', body={'data': {'page_name': name2}})
        self.assert_code(errors.task_text_proof_duplicated, r)

    def test_api_get_compare(self):
        """ 测试选择比对文本 """

        # 测试获取比对本
        page_name = 'JX_165_7_75'
        self.login(u.expert1[0], u.expert1[1])
        r = self.parse_response(
            self.fetch('/api/task/text_proof/get_compare/%s' % page_name, body={'data': {'num': 1}}))
        self.assertTrue(r.get('cmp'))
        self.assertTrue(r.get('hit_page_codes'))
        hit_page_codes = r.get('hit_page_codes')

        # 测试获取上一页文本
        data = {'data': {'cmp_page_code': hit_page_codes[0], 'neighbor': 'prev'}}
        r = self.parse_response(self.fetch('/api/task/text_proof/get_compare_neighbor', body=data))
        self.assertTrue(r.get('txt'))

        # 测试获取下一页文本
        data = {'data': {'cmp_page_code': hit_page_codes[0], 'neighbor': 'next'}}
        r = self.parse_response(self.fetch('/api/task/text_proof/get_compare_neighbor', body=data))
        self.assertTrue(r.get('txt'))

    def test_lobby_order(self):
        """测试任务大厅的任务显示顺序"""
        self.login_as_admin()
        self.publish_tasks(dict(task_type='text_proof_1', pages='GL_1056_5_6', priority=2))
        self.publish_tasks(dict(task_type='text_proof_1', pages='JX_165_7_12', priority=3))
        self.publish_tasks(dict(task_type='text_proof_2', pages='JX_165_7_12', priority=2))
        self.publish_tasks(dict(task_type='text_proof_3', pages='JX_165_7_12', priority=1))
        self.publish_tasks(dict(task_type='text_proof_2', pages='JX_165_7_30', priority=1))

        self.login(u.expert1[0], u.expert1[1])
        for i in range(5):
            r = self.parse_response(self.fetch('/task/lobby/text_proof?_raw=1'))
            names = [t['name'] for t in r.get('tasks', [])]
            self.assertEqual(set(names), {'GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30'})
            self.assertEqual(len(names), len(set(names)))  # 不同校次的同名页面只列出一个
            self.assertEqual(names, ['JX_165_7_12', 'GL_1056_5_6', 'JX_165_7_30'])  # 按优先级顺序排列
