#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import random
import tests.users as u
from tests.testcase import APITestCase
from controller import errors as e
from controller import helper as hp
from utils.gen_chars import gen_chars


class TestPage(APITestCase):

    def setUp(self):
        super(TestPage, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家,数据管理员,单元测试用户'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.proof1, u.proof2, u.proof3]],
            '普通用户,单元测试用户,切分校对员,聚类校对员,生僻校对员'
        )
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.review1, u.review2, u.review3]],
            '普通用户,单元测试用户,切分审定员,聚类审定员,生僻审定员'
        )
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestPage, self).tearDown()

    @staticmethod
    def get_post_data(page, task_type=None, step=None):
        data = {k: page.get(k) for k in ['chars', 'columns', 'blocks']}
        if task_type:
            data['task_type'] = task_type
        if step:
            data['step'] = step
        return data

    def test_page_box_api(self):
        """ 测试切分校对"""
        name = 'QL_25_416'
        task_type = 'cut_proof'
        # 发布任务
        r = self.publish_page_tasks(dict(page_names=name, task_type=task_type, pre_tasks=[]))
        self.assert_code(200, r)
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': name})

        # 以校对员身份登录并领取任务
        self.login(u.proof1[0], u.proof1[1])
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
        self.assert_code(200, r)

        # 1. 测试以任务方式增删改
        # 测试修改数据
        page = self._app.db.page.find_one({'name': name})
        page['chars'][0].update({'changed': True, 'w': page['chars'][0]['w'] + 1})
        page['blocks'][0].update({'changed': True, 'w': page['blocks'][0]['w'] + 1})
        page['columns'][0].update({'changed': True, 'w': page['columns'][0]['w'] + 1})
        url = '/api/task/do/%s/%s' % (task_type, task['_id'])
        r = self.fetch(url, body={'data': self.get_post_data(page, 'cut_proof', 'box')})
        self.assert_code(200, r)
        page1 = self._app.db.page.find_one({'name': name})
        self.assertIsNotNone(page1['chars'][0]['box_logs'])
        self.assertIsNotNone(page1['chars'][0]['box_level'])
        self.assertIsNotNone(page1['blocks'][0]['box_logs'])
        self.assertIsNotNone(page1['blocks'][0]['box_level'])
        self.assertIsNotNone(page1['columns'][0]['box_logs'])
        self.assertIsNotNone(page1['columns'][0]['box_level'])
        self.assertEqual(len(page['chars']), len(page1['chars']))
        # 测试新增数据
        page1['chars'].append({'x': 1, 'y': 1, 'w': 10, 'h': 10, 'added': True})
        page1['chars'].append({'x': 2, 'y': 2, 'w': 20, 'h': 20, 'added': True})
        r = self.fetch(url, body={'data': self.get_post_data(page1, 'cut_proof', 'box')})
        self.assert_code(200, r)
        page2 = self._app.db.page.find_one({'name': name})
        self.assertEqual(len(page1['chars']), len(page2['chars']))
        # 测试删除数据
        page2['chars'].pop(-1)
        r = self.fetch(url, body={'data': self.get_post_data(page2, 'cut_proof', 'box')})
        self.assert_code(200, r)
        page3 = self._app.db.page.find_one({'name': name})
        self.assertEqual(len(page2['chars']), len(page3['chars']))

        # 2. 测试直接增删改
        # 测试积分不够，无法修改数据
        page4 = self._app.db.page.find_one({'name': name})
        page4['chars'][1].update({'changed': True, 'w': page4['chars'][1]['w'] + 1})
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page4)})
        self.assert_code(200, r)
        page5 = self._app.db.page.find_one({'name': name})
        self.assertIsNone(page5['chars'][1].get('box_logs'))

        # 测试积分不够，无法删除数据
        page5['chars'].pop(-1)
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page5)})
        self.assert_code(200, r)
        page6 = self._app.db.page.find_one({'name': name})
        self.assertEqual(len(page6['chars']), len(page5['chars']) + 1)

        # 测试新增数据，不需要积分
        page6['chars'].append({'x': 1, 'y': 1, 'w': 10, 'h': 10, 'added': True})
        page6['chars'].append({'x': 2, 'y': 2, 'w': 20, 'h': 20, 'added': True})
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page6)})
        self.assert_code(200, r)
        page7 = self._app.db.page.find_one({'name': name})
        self.assertEqual(len(page7['chars']), len(page6['chars']))

        # 3. 测试专家直接修改
        self.login(u.expert1[0], u.expert1[1])

        # 测试专家可以删除数据
        page7['chars'].pop(-1)
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page7)})
        self.assert_code(200, r)
        page8 = self._app.db.page.find_one({'name': name})
        self.assertEqual(len(page8['chars']), len(page7['chars']))

        # 测试专家可以修改数据
        page8['chars'][2].update({'changed': True, 'w': page8['chars'][2]['w'] + 1})
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page8)})
        self.assert_code(200, r)
        page9 = self._app.db.page.find_one({'name': name})
        self.assertIsNotNone(page9['chars'][2]['box_logs'])
        self.assertIsNotNone(page9['chars'][2]['box_level'])

    def test_page_box_view(self):
        name = 'QL_25_733'
        self.login(u.expert1[0], u.expert1[1])

        # 专家修改数据
        page = self._app.db.page.find_one({'name': name})
        page['chars'][0].update({'changed': True, 'w': page['chars'][0]['w'] + 1})
        r = self.fetch('/api/page/box/' + name, body={'data': self.get_post_data(page)})
        self.assert_code(200, r)
        page1 = self._app.db.page.find_one({'name': name})
        self.assertIsNotNone(page1['chars'][0].get('box_logs'))
        self.assertIsNotNone(page1['chars'][0].get('box_level'))

        # 测试专家进入页面，检查第一个char的权限为读写
        d = self.parse_response(self.fetch('/page/box/' + name + '?_raw=1'))
        char = hp.prop(d, 'page.chars')[0]
        self.assertFalse(char.get('readonly'))

        # 测试校对员进入页面，检查第一个char的权限为只读
        self.login(u.proof1[0], u.proof1[1])
        d1 = self.parse_response(self.fetch('/page/box/' + name + '?_raw=1'))
        char1 = hp.prop(d1, 'page.chars')[0]
        self.assertTrue(char1.get('readonly'))

    def test_char_box(self):
        """ 测试修改字框"""
        name = 'GL_1056_5_6_12'
        page_name, cid = '_'.join(name.split('_')[:-1]), int(name.split('_')[-1])
        char = self._app.db.char.find_one({'name': name})
        page = self._app.db.page.find_one({'name': page_name, 'chars.cid': cid}, {'name': 1, 'chars.$': 1})
        if not char or not page:
            return
        else:
            cond = {'name': page_name, 'chars.cid': cid}
            self._app.db.page.update_one(cond, {'$unset': {'chars.$.box_level': '', 'chars.$.box_logs': ''}})

        # 以审定员身份登录
        self.login(u.review1[0], u.review1[1])
        # 测试以任务方式修改数据
        char['pos']['w'] += 1
        data = {'pos': char['pos'], 'task_type': 'cut_review'}
        r = self.fetch('/api/char/box/' + name, body={'data': data})
        self.assert_code(200, r)
        char1 = self._app.db.char.find_one({'name': name})
        self.assertEqual(char1['pos']['w'], char['pos']['w'])
        page1 = self._app.db.page.find_one({'name': page_name, 'chars.cid': cid}, {'name': 1, 'chars.$': 1})
        self.assertEqual(page1['chars'][0]['w'], char['pos']['w'])
        self.assertIsNotNone(page1['chars'][0]['box_logs'])
        # 测试直接修改——积分不够，无法修改
        data1 = {'pos': char['pos']}
        r = self.fetch('/api/char/box/' + name, body={'data': data1})
        self.assert_code(e.data_point_unqualified, r)
        # 测试以校对员身份登录，以任务方式修改数据——数据等级不够
        self.login(u.proof1[0], u.proof1[1])
        data = {'pos': char['pos'], 'task_type': 'cut_proof'}
        r = self.fetch('/api/char/box/' + name, body={'data': data})
        self.assert_code(e.data_level_unqualified, r)
        # 测试以专家身份登录，可以直接修改数据
        self.login(u.expert1[0], u.expert1[1])
        char['pos']['w'] += 2
        data = {'pos': char['pos']}
        r = self.fetch('/api/char/box/' + name, body={'data': data})
        char1 = self._app.db.char.find_one({'name': name})
        self.assertEqual(char1['pos']['w'], char['pos']['w'])

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

    def test_page_update(self):
        page = self._app.db.page.find_one()
        data = {'_id': str(page['_id']), 'name': page['name'], "remark_box": "不合要求%s" % random.randint(0, 9999)}
        r = self.fetch('/api/page', body={'data': data})
        self.assert_code(200, r)
