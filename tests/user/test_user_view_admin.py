#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import re
import tests.users as u
from controller import views
from tests.testcase import APITestCase


class TestUserAdminViews(APITestCase):
    def setUp(self):
        super(TestUserAdminViews, self).setUp()

    def test_view_user_admin(self):
        """用户管理页面"""
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/user/admin')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[0], data)

    def test_view_user_role(self):
        """角色管理页面"""
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/user/role')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[0], data)

    def test_view_user_statistic(self):
        """数据统计页面"""
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin([dict(email=u.user1[0], password=u.user1[1], name=u.user1[2])])
        r = self.fetch('/user/statistic')
        self.assert_code(200, r)
        data = self.parse_response(r)
        self.assertIn(u.user1[2], data)

    def test_user_views(self):
        """URL的合法性"""
        for view in views:
            pkg = re.sub(r'^.+controller\.', '', str(view)).split('.')[0]
            if isinstance(view.URL, str) and '(' not in view.URL and '@' not in view.URL:  # URL不需要动态参数
                r = self.parse_response(self.fetch(view.URL + '?_no_auth=1'))
                self.assertTrue('currentUserId' in r, msg=view.URL + re.sub(r'(\n|\s)+', '', str(r))[:120])
                if pkg not in ['com', 'tripitaka']:
                    self.assertRegex(view.URL, r'^/%s(/|$)' % pkg, msg=view.URL)
            elif isinstance(view.URL, list):
                for _url in view.URL:
                    if pkg not in ['com', 'tripitaka'] and '/data/edit' not in _url:
                        self.assertRegex(_url, r'^/%s(/|$)' % pkg, msg=_url)
