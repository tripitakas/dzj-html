#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from controller import auth
from controller import views
from controller import validate as v
from tests.testcase import APITestCase


class TestCom(APITestCase):
    def setUp(self):
        super(TestCom, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_api_404(self):
        """ 不存在的API接口"""
        r = self.fetch('/api/xyz')
        self.assert_code(404, r)
        data = self.parse_response(r)
        self.assertEqual(data.get('code'), 404)

    def test_auth(self):
        """ 测试auth模块"""
        # 测试can_access
        self.assertFalse(auth.can_access('', '/api/task/pick/cut_proof', 'POST'))
        self.assertTrue(auth.can_access('切分专家', '/api/task/pick/cut_proof', 'POST'))
        self.assertEqual(auth.get_route_roles('/api/task/pick/cut_proof', 'POST'), ['切分校对员', '切分专家'])
        # 测试get_all_roles
        roles = auth.get_all_roles('切分专家,文字专家')
        should = {'普通用户', '切分专家', '文字专家', '切分审定员', '切分校对员', 'OCR校对员', 'OCR审定员', '文字校对员', '文字审定员'}
        self.assertEqual(set(roles), should)

    def test_validate(self):
        """ 测试validate模块"""
        data = {'name': '1234567890', 'phone': '', 'email': '', 'password': '', 'age': 8}
        rules = [
            (v.allowed_keys, 'name', 'phone', 'email', 'password'),
            (v.not_empty, 'name', 'password'),
            (v.not_both_empty, 'phone', 'email'),
            (v.is_name, 'name'),
            (v.is_phone, 'phone'),
            (v.is_email, 'email'),
            (v.is_password, 'password'),
            (v.between, 'age', 10, 100),
        ]
        errs = v.validate(data, rules)
        self.assertEqual(set(errs.keys()), {'age', 'email', 'name', 'password', 'phone'})
        for k, t in errs.items():
            self.assertIs(t.__class__, tuple)
            self.assertIs(t[0].__class__, int)
            self.assertIs(t[1].__class__, str)

    def test_com_search(self):
        q = '夫宗極絕於稱謂賢聖以之沖默玄旨非言'
        r = self.fetch('/api/com/search', body={'data': {'q': q}})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('matches', r)

    def test_com_punctuate(self):
        q = '初靜慮地受生諸天即受彼地離生喜樂第二靜慮地諸天受定生喜樂'
        r = self.fetch('/api/com/punctuate', body={'data': {'q': q}})
        self.assert_code(200, r)

    def _test_url_validate(self):
        """ URL的合法性"""
        for view in views:
            pkg = re.sub(r'^.+controller\.', '', str(view)).split('.')[0]
            if isinstance(view.URL, str) and '(' not in view.URL and '@' not in view.URL:  # URL不需要动态参数
                r = self.parse_response(self.fetch(view.URL + '?_no_auth=1'))
                self.assertTrue('currentUserId' in r, msg=view.URL + re.sub(r'(\n|\s)+', '', str(r))[:120])
                if pkg not in ['com', 'tripitaka']:
                    self.assertRegex(view.URL, r'^/%s(/|$)' % pkg, msg=view.URL)
            elif isinstance(view.URL, list):
                for _url in view.URL:
                    if pkg not in ['com', 'tripitaka'] and not ('/data/' in _url and 'edit' in _url):
                        self.assertRegex(_url, r'^/%s(/|$)' % pkg, msg=_url)
