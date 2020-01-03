#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tests.users as u
from tests.testcase import APITestCase
from tornado.escape import json_encode
from controller.cut.cuttool import CutTool


class TestCutSave(APITestCase):
    """ 测试 CutTaskApi.post """

    def setUp(self):
        super(TestCutSave, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]],
            '切分专家,文字专家'
        )
        self.delete_tasks_and_locks()
        self.doc_id = 'QL_25_16'
        self.old_page = self._app.db.page.find_one({'name': self.doc_id})

    def tearDown(self):
        self._app.db.page.update_one({'name': self.doc_id}, {'$set': self.old_page})
        super(TestCutSave, self).tearDown()

    def _test_save_proof(self, kind, step=None, do_change=None, for_save=None):
        task_type = 'cut_proof'
        data_field = kind + 's'
        step = step or kind + 's'

        # 发布任务
        self.login_as_admin()
        r = self.publish_page_tasks(dict(doc_ids=[self.doc_id], task_type=task_type, pre_tasks=[], steps=[step]))
        self.assert_code(200, r)

        # 领取指定的任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': task_type, 'doc_id': self.doc_id})
        r = self.fetch('/api/task/pick/' + task_type, body={'data': {'task_id': task['_id']}})
        self.assert_code(200, r)

        page = self._app.db.page.find_one({'name': self.doc_id})
        if do_change:
            do_change(page)
        else:
            # 加一个框
            box = page[data_field][-1]
            page[data_field].append(dict(x=box['x'], y=box['y'] + box['h'], w=box['w'], h=box['h']))
            if len(page[data_field]) > 2:
                page[data_field].pop(0)  # 删一个框

        # 保存
        data = {'step': step, 'boxes': json_encode(page[data_field])}
        for_save and for_save(data)
        r = self.fetch('/api/task/do/%s/%s' % (task_type, task['_id']), body={'data': data})
        self.assert_code(200, r, msg=task_type + ':' + step)

        # 结果应已重新计算序号
        page_res = self._app.db.page.find_one({'name': self.doc_id})
        self.assertEqual(len(page_res[data_field]), len(page[data_field]))
        self.assertTrue(all([c.get(kind + '_id') for c in page_res[data_field]]))

        # 其他两种切分框不应改变
        for k in ['blocks', 'columns', 'chars']:
            if k != data_field:
                self.assertEqual(self.old_page[k], page_res[k])

        return page_res

    def test_save_block_proof(self):
        """ 栏框校对: 把blocks数据传给后台，后台保存blocks，重新计算序号 """
        page = self._test_save_proof('block')
        self.assertEqual([c.get('block_id') for c in page['blocks']], ['b1', 'b2'])

    def test_save_column_proof(self):
        """ 列框校对: 把columns数据传给后台，后台保存columns，然后重新计算序号 """
        page = self._test_save_proof('column')
        self.assertEqual([c.get('column_id') for c in page['columns']],
                         ['b1c1', 'b1c2', 'b1c3', 'b1c4', 'b1c5', 'b1c6', 'b1c7', 'b1c8', 'b1c9'])

    def test_save_char_proof(self):
        """ 字框校对：把chars数据传给后台，后台保存chars，如果有增、删字框，则重新计算序号 """
        page = self._test_save_proof('char')
        self.assertEqual([c.get('char_id') for c in page['chars'][:3]], ['b1c1c1', 'b1c1c2', 'b1c1c3'])
        self.assertEqual([c.get('char_id') for c in page['chars'][-5:]],
                         ['b1c7c24', 'b1c8c1', 'b1c8c2', 'b1c9c1', 'b1c9c2'])
        self.assertEqual([c.get('char_id') for c in self.old_page['chars'][:3]], ['b1c1c1', 'b1c1c2', 'b1c1c3'])
        self.assertEqual([c.get('char_id') for c in self.old_page['chars'][-5:]],
                         ['b1c7c23', 'b1c7c24', 'b1c8c1', 'b1c8c2', 'b1c9c1'])

    def test_save_char_order(self):
        """ 字序校对：把chars_col数据传给后台，后台根据chars_col重新计算字序 """
        def change(p):
            chars_col.extend(CutTool.char_render(p, 0)['chars_col'])
            # 0 = [1, 2, 3, 4]
            # 1 = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
            chars_col[0].append(chars_col[1].pop(0))

        chars_col = []
        page = self._test_save_proof('char', step='orders', do_change=change,
                                     for_save=lambda d: d.update({'chars_col': chars_col}))
        self.assertEqual([c.get('char_id') for c in page['chars'][:6]],
                         ['b1c1c1', 'b1c1c2', 'b1c1c3', 'b1c1c4', 'b1c1c5', 'b1c2c1'])
