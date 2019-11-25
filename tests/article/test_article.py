#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tests.testcase import APITestCase
from controller.text.diff import Diff


class TestArticle(APITestCase):
    def setUp(self):
        super(TestArticle, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_article_simple(self):
        self.assert_code(200, self.fetch('/article/edit/new?_raw=1'))
        r = self.fetch('/api/article/save/new', body={'data': dict(title='Test', category='test', content='?')})
        r = self.parse_response(r)
        self.assertIn('id', r)
        r = self.parse_response(self.fetch('/article/edit/%s?_raw=1' % r['id']))
        self.assertIn('article', r)
