#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tests.users as u
from controller import errors as e
from tests.testcase import APITestCase


class TestCutTask(APITestCase):

    def setUp(self):
        super(TestCutTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,数据管理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1, u.user2, u.user3]],
            '普通用户,单元测试用户'
        )
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestCutTask, self).tearDown()

    def test_page_box(self):
        """ 测试切分校对"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        name = 'YB_22_346'
        r = self.fetch('/page/box/edit/%s?_raw=1' % name)
        d = self.parse_response(r)
        self.assertFalse(d.get('readonly'))
        # 测试提交修改
        page = self._app.db.page.find_one({'name': name})
        page['chars'].pop(-1)
        page['chars'].append({'x': 1, 'y': 1, 'w': 10, 'h': 10, 'added': True})
        page['chars'][0].update({'changed': True, 'w': page['chars'][0]['w'] + 1})
        page['blocks'][0].update({'changed': True, 'w': page['blocks'][0]['w'] + 1})
        page['columns'][0].update({'changed': True, 'w': page['columns'][0]['w'] + 1})
        data = {k: page.get(k) for k in ['chars', 'columns', 'blocks']}
        r = self.fetch('/api/page/box/' + name, body={'data': data})
        self.assert_code(200, r)

    def test_page_txt(self):
        """ 测试文字校对"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        name = 'YB_22_346'
        r = self.fetch('/page/txt/edit/%s?_raw=1' % name)
        d = self.parse_response(r)

    def test_page_list(self):
        """ 测试数据管理-页数据"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        r = self.fetch('/page/list?_raw=1')
        d = self.parse_response(r)
        print(d)