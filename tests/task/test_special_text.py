#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestSpecialText(APITestCase):

    def test_utf8mb4(self):
        r = self.fetch('/api/page/GL_1056_5_6')
        self.assert_code(200, r)
        txt = self.parse_response(r).get('txt', '')
        self.assertIn('卷北鿌沮渠蒙遜', txt)
        self.assertIn('\U0002e34f', txt)


class TestPages(APITestCase):

    def test_pages(self):

        # 准备发布任务，得到页名
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={}))
        self.assertIn('items', r)
        self.assertIsInstance(r['items'][0], str)
        names = r['items']

        # 先发布一种任务类型
        self.login_as_admin()
        self.fetch('/api/start/', body=dict(data=dict(types='char_cut_proof')))

        # 因为还有其他任务类型，所以得到的页名没少
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={}))
        self.assertEqual(len(r['items']), len(names))

        # 如果取同一类型则没有空闲页名了
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={'data': dict(types='char_cut_proof')}))
        self.assertEqual(len(r['items']), 0)
        # 也不能再发布同一类型的任务了
        self.fetch('/api/start/', body=dict(data=dict(types='char_cut_proof')))
        self.assertEqual(len(r['items']), 0)

        # 还可以发布其他类型的任务
        r = self.parse_response(self.fetch('/api/pages/cut_start', body={'data': dict(types='column_cut_proof')}))
        self.assertIn('items', r)
        self.assertEqual(len(r['items']), len(names))

        # 清空任务
        self.fetch('/api/unlock/cut_proof/')
        self.fetch('/api/start/', body=dict(data=dict(types='char_cut_proof')))
        self.assertEqual(len(r['items']), len(names))
