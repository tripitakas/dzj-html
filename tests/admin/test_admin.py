#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tests.testcase import APITestCase
from controller.text.diff import Diff


class TestArticle(APITestCase):
    def setUp(self):
        super(TestArticle, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_view_404(self):
        """测试不存在的页面"""
        self.assert_code(404, self.fetch('/xyz'))

    def test_view_show_api(self):
        r = self.parse_response(self.fetch('/api?_raw=1'))
        self.assertIn('handlers', r)
        for url, func, repeat, file, comment, auth in r['handlers']:
            # 控制器类的get/post方法需要写简要的文档字符串
            self.assertNotIn(comment, ['', 'None', None], '%s %s need doc comment' % (url, func))

            r2 = self.fetch('/api/code/%s?_raw=1' % (func,))
            self.assertEqual(self.parse_response(r2).get('name'), func)
