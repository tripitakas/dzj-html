#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from glob2 import glob
import controller.errors as e
from tests.testcase import APITestCase


class TestVariantApi(APITestCase):

    def setUp(self):
        super(TestVariantApi, self).setUp()
        self.add_first_user_as_admin_then_login()

    def tearDown(self):
        super(TestVariantApi, self).tearDown()

    def test_variant_add_or_update(self):
        # 清空图片字
        self._app.db.variant.delete_many({'nor_txt': '勝'})
        # 测试新增一条文字异体字
        r = self.fetch('/api/variant/upsert', body={'data': dict(txt='胜', nor_txt='勝')})
        self.assert_code(200, r)

        # 测试新增一条图片异体字
        img_name = 'GL_8_5_10_1'
        r = self.fetch('/api/variant/upsert', body={'data': dict(img_name=img_name, user_txt='胜')})
        self.assert_code(200, r)

        # 测试递归正字
        vt = self._app.db.variant.find_one({'img_name': img_name})
        self.assertEqual(vt.get('nor_txt'), '勝')

        # 测试图片编码已存在
        r = self.fetch('/api/variant/upsert', body={'data': dict(img_name=img_name, user_txt='勝')})
        self.assert_code(e.variant_exist, r)

    def test_variant_delete(self):
        variants = list(self._app.db.variant.find().limit(5))
        # 测试删除一条记录
        _id = variants[0].get('_id')
        r = self.fetch('/api/data/variant/delete', body={'data': {'_id': _id}})
        self.assert_code(200, r)

        # 测试删除多条记录
        _ids = [r.get('_id') for r in variants]
        r = self.fetch('/api/data/variant/delete', body={'data': {'_ids': _ids}})
        self.assert_code(200, r)
