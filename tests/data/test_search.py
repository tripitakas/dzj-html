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
        self.delete_all_tasks()

    def tearDown(self):
        super(TestSearch, self).tearDown()

    def test_api_cbeta_search(self):
        q = '夫宗極絕於稱謂賢聖以之沖默玄旨非言'
        r = self.fetch('/api/data/cbeta_search', body={'data': {'q': q}})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('matches', r)

    def test_api_punctuation(self):
        q = '初靜慮地受生諸天即受彼地離生喜樂第二靜慮地諸天受定生喜樂'
        r = self.fetch('/api/data/punctuation', body={'data': {'q': q}})
        self.assert_code(200, r)
