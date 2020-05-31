#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
from os import path
import tests.users as u
from tests.testcase import APITestCase
from utils.gen_chars import gen_chars


class TestCutTask(APITestCase):

    def setUp(self):
        super(TestCutTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,数据管理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.user1, u.user2, u.user3]],
            '普通用户,单元测试用户'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestCutTask, self).tearDown()

    def test_page_upload(self):
        # 测试上传文件
        filename = path.join(self._app.BASE_DIR, 'meta', 'meta', 'pages.json')
        if not path.exists(filename):
            return

        # 清空上次的数据
        with open(filename, 'r') as fn:
            page_names = json.load(fn)
            self._app.db.page.delete_many({'name': {'$in': page_names}})

        r = self.fetch('/api/data/page/upload', files={'json': filename}, body={'data': {'layout': '上下一栏'}})
        self.assert_code(200, r)

    def test_page_nav(self):
        r = self.fetch('/page/browse/JX_165_7_12?to=next&_raw=1')
        self.assert_code(200, r)
        r = self.fetch('/page/browse/JX_165_7_12?to=prev&_raw=1')
        self.assert_code(200, r)

    def test_page_export_char(self):
        pages = self._app.db.page.find({'name': {'$regex': 'GL'}})
        page_names = [p['name'] for p in list(pages)]
        r = self.fetch('/api/data/page/export_char', body={'data': {'page_names': page_names}})
        self.assert_code(200, r)

    def test_page_box(self):
        """ 测试切分校对"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        name = 'YB_22_346'
        r = self.fetch('/page/box/edit/%s?_raw=1' % name)
        d = self.parse_response(r)
        self.assertFalse(d.get('readonly'))
        # 测试提交修改
        page = self._app.db.page.find_one({'name': name})
        page['chars'].pop(-1)
        page['chars'].append({'x': 1, 'y': 1, 'w': 10, 'h': 10, 'added': True})
        page['chars'][0].update({'changed': True, 'w': page['chars'][0]['w'] + 1})
        page['blocks'][0].update({'changed': True, 'w': page['blocks'][0]['w'] + 1})
        page['columns'][0].update({'changed': True, 'w': page['columns'][0]['w'] + 1})
        data = {k: page.get(k) for k in ['chars', 'columns', 'blocks']}
        r = self.fetch('/api/page/box/' + name, body={'data': data})
        self.assert_code(200, r)

    def test_page_txt(self):
        """ 测试文字校对"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        name = 'YB_22_346'
        r = self.fetch('/page/txt/edit/%s?_raw=1' % name)
        d = self.parse_response(r)

    def test_page_list(self):
        """ 测试数据管理-页数据"""
        self.login(u.expert1[0], u.expert1[1])
        # 测试进入页面
        r = self.fetch('/page/list?_raw=1')
        d = self.parse_response(r)
        print(d)

    def test_gen_chars(self):
        """ 测试生成字表"""
        self._app.db.char.delete_many({})
        # 测试从page生成char数据
        name = 'YB_22_346'
        gen_chars(self._app.db, page_names=name)
        page = self._app.db.page.find_one({'name': name}, {'chars': 1})
        cnt = self._app.db.char.count_documents({})
        self.assertEqual(cnt, len(page['chars']))
        # 测试删除和更新char数据
        ch = page['chars'][0]
        ch['w'] += 1
        del page['chars'][-1]
        self._app.db.page.update_one({'_id': page['_id']}, {'$set': {'chars': page['chars']}})
        gen_chars(self._app.db, page_names=name)
        page = self._app.db.page.find_one({'name': name}, {'chars': 1})
        cnt = self._app.db.char.count_documents({})
        self.assertEqual(cnt, len(page['chars']))
        char = self._app.db.char.find_one({'name': 'YB_22_346_%s' % ch['cid']})
        self.assertEqual(char['pos']['w'], ch['w'])
