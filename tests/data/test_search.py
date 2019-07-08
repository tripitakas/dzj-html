#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tests.users as u
from tests.testcase import APITestCase


class TestSearch(APITestCase):
    def setUp(self):
        super(TestSearch, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        self.revert()

    def tearDown(self):
        super(TestSearch, self).tearDown()

    def test_view_cbeta_search(self):
        q = '夫宗極絕於稱謂，賢聖以之沖默；玄旨非言'
        r = self.fetch('/data/cbeta/search?q=%s&_no_auth=1' % q)
        self.assert_code(200, r)

    def test_api_get_cmp(self):
        """ 测试获取比对文本 """
        page_name = 'JX_165_7_75'
        self.login(u.expert1[0], u.expert1[1])

        r = self.parse_response(
            self.fetch('/api/task/text_proof/get_cmp/%s' % page_name, body={'data': {'num': 1}}))
        self.assertTrue(r.get('cmp'))
        self.assertTrue(r.get('hit_page_codes'))

        data = {'data': {'cmp_page_code': r.get('hit_page_codes')[0], 'neighbor': 'prev'}}
        r = self.parse_response(self.fetch('/api/task/text_proof/get_cmp_neighbor', body=data))
        self.assertTrue(r.get('txt'))
