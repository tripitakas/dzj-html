#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from controller import errors as e
from tests.testcase import APITestCase
from tornado.escape import json_encode


class TestTextTask(APITestCase):
    def setUp(self):
        super(TestTextTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3, u.expert3]],
            '切分专家,文字专家'
        )
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestTextTask, self).tearDown()

    def test_text_task_flow(self):
        """ 测试文字任务流程 """
        docs_ready = ['GL_1056_5_6', 'JX_165_7_12']
        users = [u.expert1, u.expert2, u.expert3, u.expert4]
        page1 = self._app.db.page.find_one({'name': docs_ready[0]})
        # 发布并完成文字校一、校二、校三
        for i, task_type in enumerate(['text_proof_1', 'text_proof_2', 'text_proof_3']):
            # 发布任务
            self.login_as_admin()
            r = self.publish_page_tasks(dict(task_type=task_type, doc_ids=docs_ready, pre_tasks=[]))
            self.assert_code(200, r)

            # 领取任务
            self.login(users[i][0], users[i][1])
            task1 = self._app.db.task.find_one({'task_type': task_type, 'doc_id': docs_ready[0]})
            r = self.fetch('/api/task/pick/%s' % task_type, body={'data': {'task_id': task1['_id']}})
            self.assert_code(200, r)

            # 第一步：选择比对文本
            r = self.fetch('/task/do/%s/%s?step=select&_raw=1' % (task_type, task1['_id']))
            self.assert_code(200, r)

            # 测试获取比对本
            r = self.fetch('/api/task/text_select/%s' % docs_ready[0], body={'data': {'num': 1}})
            data = self.parse_response(r)
            self.assertTrue(data.get('cmp'))
            self.assertTrue(data.get('hit_page_codes'))

            # 提交第一步
            r = self.fetch(
                '/api/task/do/%s/%s' % (task_type, task1['_id']),
                body={'data': dict(submit=True, cmp=data.get('cmp'), step='select')}
            )
            self.assert_code(200, r)
            task = self._app.db.task.find_one({'_id': task1['_id']})
            self.assertIn('select', task['steps']['submitted'])

            # 第二步：文字校对
            r = self.fetch('/task/do/%s/%s?step=proof&_raw=1' % (task_type, task1['_id']))
            self.assert_code(200, r)

            # 提交第二步
            r = self.fetch(
                '/api/task/do/%s/%s?_raw=1' % (task_type, task1['_id']),
                body={'data': dict(submit=True, txt_html=json_encode(page1.get('ocr')), step='proof')}
            )
            self.assert_code(200, r)

        # 发布审定任务
        self.login_as_admin()
        r = self.publish_page_tasks(dict(task_type='text_review', doc_ids=docs_ready))
        self.assert_code(200, r)
        self.assertEqual(self.parse_response(r).get('published'), [docs_ready[0]])

        # 领取文字审定
        task2 = self._app.db.task.find_one({'task_type': 'text_review', 'doc_id': docs_ready[0]})
        r = self.fetch('/api/task/pick/text_review', body={'data': {'task_id': task2['_id']}})
        self.assert_code(200, r)

        # 完成文字审定
        doubt = "<tr class='char-list-tr' data='line-8' data-offset='10' data-reason='理由1'>" \
                "<td>8</td><td>10</td><td>存疑内容一</td><td>理由1</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>" \
                "<tr class='char-list-tr' data='line-3' data-offset='6' data-reason='理由2'>" \
                "<td>3</td><td>6</td><td>存疑内容二</td><td>理由2</td><td class='del-doubt'>" \
                "<img src='/static/imgs/del_icon.png' )=''></td></tr>"
        r = self.fetch('/api/task/do/text_review/%s?_raw=1' % task2['_id'],
                       body={'data': dict(submit=True, txt_html=json_encode(page1.get('ocr')), doubt=doubt)})
        self.assert_code(200, r)

        # 难字任务大厅应有任务
        r = self.parse_response(self.fetch('/task/lobby/text_hard?_raw=1'))
        docs = [t['doc_id'] for t in r.get('tasks', [])]
        self.assertEqual(set(docs), {docs_ready[0]})

        # 领取难字审定
        r = self.fetch('/api/task/pick/text_hard', body={'data': {}})
        self.assert_code(200, r)

        # 完成难字审定
        data = self.parse_response(r)
        r = self.fetch('/api/task/do/text_hard/%s?_raw=1' % data.get('task_id'),
                       body={'data': dict(submit=True, txt_html=json_encode(page1.get('ocr')))})
        self.assert_code(200, r)

        # 测试文字编辑
        r = self.fetch('/page/edit/text/%s?_raw=1' % docs_ready[0])
        self.assert_code(200, r)

        # 保存文字编辑
        r = self.fetch('/api/page/edit/text/%s' % docs_ready[0],
                       body={'data': dict(submit=True, txt_html=json_encode(page1.get('ocr')))})
        self.assert_code(200, r)

    def test_api_get_compare(self):
        """ 测试选择比对文本 """

        # 测试获取比对本
        page_name = 'QL_25_16'
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/task/text_select/%s' % page_name, body={'data': {'num': 1}})
        d = self.parse_response(r)
        self.assertTrue(d.get('cmp'))
        self.assertTrue(d.get('hit_page_codes'))
        hit_page_codes = d.get('hit_page_codes')

        # 测试获取上一页文本
        data = {'data': {'cmp_page_code': hit_page_codes[0], 'neighbor': 'prev'}}
        d = self.parse_response(self.fetch('/api/task/text_neighbor', body=data))
        self.assertTrue(d.get('txt'))

        # 测试获取下一页文本
        data = {'data': {'cmp_page_code': hit_page_codes[0], 'neighbor': 'next'}}
        d = self.parse_response(self.fetch('/api/task/text_neighbor', body=data))
        self.assertTrue(d.get('txt'))

    def test_text_mode(self):
        """测试文字页面的几种模式"""

        task_type = 'text_review'
        docs_ready = ['QL_25_16']
        page = self._app.db.page.find_one({'name': 'QL_25_16'})

        # 发布任务
        self.login_as_admin()
        r = self.publish_page_tasks(dict(doc_ids=docs_ready, task_type=task_type, pre_tasks=[]))
        self.assert_code(200, r)

        # 用户expert1领取指定的任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': 'QL_25_16'})
        r = self.fetch('/api/task/pick/text_review', body={'data': {'task_id': task['_id']}})
        self.assert_code(200, r)

        # 用户expert1提交任务
        data = dict(submit=True, txt_html=json_encode(page.get('ocr')))
        r = self.fetch('/api/task/do/text_review/%s' % task['_id'], body={'data': data})
        self.assert_code(200, r)

        # 测试专家expert2可以进入edit页面
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/edit/text/QL_25_16?_raw=1')
        self.assert_code(200, r)

        # 测试用户expert1进入update页面时报错
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/task/update/text_review/%s?_raw=1' % task['_id'])
        self.assert_code(e.data_is_locked, r)

        # 专家expert2离开时解锁
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/api/data/unlock/text/QL_25_16', body={'data': {}})
        self.assert_code(200, r)

        # 测试用户expert1进入update页面时为可写
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/task/update/text_review/%s?_raw=1' % task['_id'])
        self.assert_code(200, r)

        # 测试专家expert2进入edit页面时为只读
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/edit/text/QL_25_16?_raw=1')
        self.assert_code(e.data_is_locked, r)

        # 用户expert1离开时解锁
        self.login(u.expert1[0], u.expert1[1])
        r = self.fetch('/api/data/unlock/text/QL_25_16', body={'data': {}})
        self.assert_code(200, r)

        # 测试专家expert2进入edit页面时为可写
        self.login(u.expert2[0], u.expert2[1])
        r = self.fetch('/page/edit/text/QL_25_16?_raw=1')
        self.assert_code(200, r)
