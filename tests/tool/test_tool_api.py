#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from urllib.parse import urlencode
from controller import errors
import tests.users as u


class TestToolApi(APITestCase):
    def setUp(self):
        super(TestToolApi, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家'
        )
        self.delete_tasks_and_locks()

    def tearDown(self):
        super(TestToolApi, self).tearDown()

    def test_api_search(self):
        q = '夫宗極絕於稱謂賢聖以之沖默玄旨非言'
        r = self.fetch('/api/tool/search', body={'data': {'q': q}})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('matches', r)

    def test_api_punctuate(self):
        q = '初靜慮地受生諸天即受彼地離生喜樂第二靜慮地諸天受定生喜樂'
        r = self.fetch('/api/tool/punctuate', body={'data': {'q': q}})
        self.assert_code(200, r)

    def _test_submit_ocr(self):
        self._app.db.page.delete_one(dict(name='JS_100_527_1'))
        r = self.fetch('/api/data/submit_ocr/JS_100_527_1.gif', body={})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('name', r)
        self.assert_code(errors.ocr_page_existed, self.fetch('/api/data/submit_ocr/JS_100_527_1.gif', body={}))

    def _test_import_image(self):
        """请求批量导入藏经图"""
        self.login(u.data1[0], u.data1[1])
        data = dict(user_code='upload', tripitaka_code='LQ', folder='5-冠導七十五法名目')
        r = self.fetch('/api/data/import_image', body={'data': data})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('names', r)

    def _test_import_meta(self):
        """生成藏册页数据并导入，启动OCR为可选(layout)"""
        self.login(u.data1[0], u.data1[1])
        data = dict(user_code='upload', tripitaka_code='LQ', layout='上下一栏')
        r = self.fetch('/api/data/import_meta', body={'data': data})
        self.assert_code(200, r)
        r = self.parse_response(r)
        self.assertIn('volumes', r)
        self.assertIn('sutras', r)
        self.assertIn('reels', r)

    def _test_page_ocr(self):
        """对已有页面启动OCR"""
        self.login(u.data1[0], u.data1[1])
        data = dict(user_code='upload', name='LQ_5_1_1', layout='上下一栏')
        r = self.fetch('http://127.0.0.1:8010/add_ocr?' + urlencode(data))
        self.assert_code(200, r)
