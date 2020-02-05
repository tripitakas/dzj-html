#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tests.testcase import APITestCase


class TestArticle(APITestCase):
    def setUp(self):
        super(TestArticle, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_article_simple(self):
        self.assert_code(200, self.fetch('/article/add?_raw=1'))
        article = dict(title='test', category='test', article_id='for-test', active='是', content='?')
        r1 = self.parse_response(self.fetch('/api/article/add', body={'data': article}))
        self.assertIn('article_id', r1)
        r2 = self.parse_response(self.fetch('/article/update/%s?_raw=1' % r1['article_id']))
        self.assertIn('article', r2)
