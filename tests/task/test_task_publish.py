#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tests.users as u
from tests.testcase import APITestCase
from controller.task.base import TaskHandler as th


class TestTaskPublish(APITestCase):

    def setUp(self):
        super(TestTaskPublish, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )
        # 初始化任务状态
        pages = self._app.db.page.find()
        for page in pages:
            for task_key, v in page.get('tasks').items():
                page['tasks'][task_key] = dict(status=th.STATUS_READY)
            for lock_key, v in page.get('lock').items():
                page['lock'][lock_key] = dict()

    def tearDown(self):
        super(TestTaskPublish, self).tearDown()

    def _publish(self, data):
        return self.fetch('/api/task/publish', body={'data': data})

    def _set_page_status(self, page_names, task_type_status_dict):
        update_value = dict()
        for task_type, status in task_type_status_dict.items():
            update_value.update({'tasks.%s.status' % task_type: status})
        self._app.db.page.update_many({'name': {'$in': page_names}}, {'$set': update_value})

    def _assert_response(self, pages, response, task_type_status_dict):
        for task_type, status in task_type_status_dict.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages))

    def _publish_many_tasks(self, task_type, pre_tasks, size):
        pages = self._app.db.page.find({}, {'name': 1}).limit(size)
        page_names = [page['name'] for page in pages]
        self._set_page_status(page_names, {task_type: th.STATUS_READY})
        r = self.parse_response(
            self._publish(dict(task_type=task_type, pre_tasks=pre_tasks, pages=','.join(page_names))))
        self.assertIn(['pending', 'published'], r['data'])

    def _publish_task(self, task_type):
        # 测试不存在的页面
        pages_un_existed = ['GL_not_existed_1', 'JX_not_existed_2']
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_un_existed))))
        self._assert_response(pages_un_existed, r, {task_type: 'un_existed'})

        # 测试未就绪的页面
        pages_un_ready = ['GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87']
        self._set_page_status(pages_un_ready, {task_type: th.STATUS_UNREADY})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_un_ready))))
        self._assert_response(pages_un_ready, r, {task_type: 'un_ready'})

        # 测试已就绪的页面
        pages_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        self._set_page_status(pages_ready, {task_type: th.STATUS_READY})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_ready))))
        self._assert_response(pages_ready, r, {task_type: 'published'})

        # 测试已发布的页面
        pages_published_before = ['YB_22_916', 'YB_22_995']
        self._set_page_status(pages_published_before, {task_type: th.STATUS_OPENED})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_published_before))))
        self._assert_response(pages_published_before, r, {task_type: 'published_before'})

        # 组合测试
        all_pages = pages_un_existed + pages_un_ready + pages_ready + pages_published_before
        self._set_page_status(pages_un_ready, {task_type: th.STATUS_UNREADY})
        self._set_page_status(pages_ready, {task_type: th.STATUS_READY})
        self._set_page_status(pages_published_before, {task_type: th.STATUS_OPENED})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(all_pages))))
        self._assert_response(pages_un_existed, r, {task_type: 'un_existed'})
        self._assert_response(pages_un_ready, r, {task_type: 'un_ready'})
        self._assert_response(pages_ready, r, {task_type: 'published'})
        self._assert_response(pages_published_before, r, {task_type: 'published_before'})

        # 还原页面状态
        self._set_page_status(pages_un_ready, {task_type: th.STATUS_READY})
        self._set_page_status(pages_published_before, {task_type: th.STATUS_READY})

    def _publish_pre_tasks(self):
        # 测试前置任务
        pages_pre_tasks = ['YB_22_713', 'YB_22_759', 'YB_22_816']
        self._set_page_status(pages_pre_tasks, {'block_cut_review': th.STATUS_READY})
        self._set_page_status(pages_pre_tasks, {'block_cut_proof': th.STATUS_READY})
        r = self.parse_response(self._publish(dict(task_type='block_cut_review', pre_tasks=['block_cut_proof'],
                                                   pages=','.join(pages_pre_tasks))))
        self._assert_response(pages_pre_tasks, r, {'block_cut_review': 'pending'})

    def _publish_file(self, task_type, txt_file, priority=1):
        body = dict(task_type=task_type, priority=priority)
        return self.fetch('/api/task/publish_file', files=dict(txt_file=txt_file), body=body)

    def _publish_tasks_file(self):
        """ 测试发布审校任务 """
        self.add_first_user_as_admin_then_login()
        pages = ['GL_1056_5_6', 'JX_165_7_12']
        self._set_page_status(pages, {'block_cut_proof': 'ready'})
        filename = './static/upload/file2upload.txt'
        with open(filename, 'w') as f:
            for page in pages:
                f.write(page + '\n')
            f.close()

        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        self.assertTrue(os.path.exists(filename))

        r = self.parse_response(self._publish_file(task_type='block_cut_proof', txt_file=filename))
        self.assertEqual(set(r.get('published')), set(pages))

        # 任务类型有误
        r = self.parse_response(self._publish_file(task_type='error_task_type', txt_file=filename))
        self.assertIn('task_type', r['error'])

    def test_publish_tasks(self):
        """ 测试发布审校任务 """
        self.add_first_user_as_admin_then_login()
        # 测试异常情况
        r = self.parse_response(self._publish(dict(task_type='block_cut_proof', pages='')))  # 页面为空
        self.assertIn('pages', r['error'])

        pages = 'GL_1056_5_6,JX_165_7_12'
        r = self.parse_response(self._publish(dict(task_type='error_task_type', pages=pages)))  # 任务类型有误
        self.assertIn('task_type', r['error'])

        # 优先级有误，必须为1/2/3
        r = self.parse_response(self._publish(dict(task_type='block_cut_proof', pages=pages, priority='高')))
        self.assertIn('priority', r['error'])

        # 测试正常情况
        self._publish_task('block_cut_proof')
        self._publish_pre_tasks()

        # 测试超大规模
        # self._publish_many_tasks('block_cut_proof', 10000)

        # 测试发布文件
        # self._publish_tasks_file()