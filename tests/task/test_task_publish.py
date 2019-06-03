#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime, date
import tests.users as u
from tests.testcase import APITestCase
from controller import errors
from controller.task.base import TaskHandler
from tornado.escape import json_encode


class TestTaskPublish(APITestCase):
    def setUp(self):
        super(TestTaskPublish, self).setUp()
        # 创建几个专家用户（权限足够），用于审校流程的测试
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1, u.expert2, u.expert3]], '切分专家,文字专家'
        )

    def tearDown(self):
        # 退回所有任务，还原改动
        for task_type in TaskHandler.task_types.keys():
            self.assert_code(200, self.fetch('/api/task/unlock/%s/' % task_type))
        for i in range(1, 4):
            self.assert_code(200, self.fetch('/api/task/unlock/text_proof.%d/' % i))
        super(TestTaskPublish, self).tearDown()

    def _publish(self, data):
        return self.fetch('/api/task/publish', body={'data': data})

    def _set_page_status(self, page_names, task_type_status_dict):
        update_value = dict()
        for task_type, status in task_type_status_dict.items():
            sub_tasks = TaskHandler.get_sub_tasks(task_type)
            if sub_tasks:
                update_value.update({'%s.%s.status' % (task_type, t): status for t in sub_tasks})
            else:
                update_value.update({'%s.status' % task_type: status})
        self._app.db.page.update_many({'name': {'$in': page_names}}, {'$set': update_value})

    def _assert_response(self, pages, response, task_type_status_dict):
        for task_type, status in task_type_status_dict.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages))

    def _publish_many_tasks(self, task_type, size):
        pages = self._app.db.page.find({}, {'name': 1}).limit(size)
        page_names = [page['name'] for page in pages]
        self._set_page_status(page_names, {task_type: TaskHandler.STATUS_READY})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(page_names))))
        status = 'pending' if TaskHandler.pre_tasks().get(task_type) else 'published'
        self.assertIn(status, r['data'])

    def _publish_task(self, task_type):
        task_type = [task_type] if isinstance(task_type, str) else task_type
        # 测试不存在的页面
        pages_un_existed = ['GL_not_existed_1', 'JX_not_existed_2']
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_un_existed))))
        self._assert_response(pages_un_existed, r, {t: 'un_existed' for t in task_type})

        # 测试未就绪的页面
        pages_un_ready = ['GL_1056_5_6', 'JX_165_7_12', 'JX_165_7_30', 'JX_165_7_75', 'JX_165_7_87']
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_UNREADY for t in task_type})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_un_ready))))
        self._assert_response(pages_un_ready, r, {t: 'un_ready' for t in task_type})

        # 测试已就绪的页面
        pages_ready = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_ready))))
        pre_tasks = TaskHandler.pre_tasks()
        self._assert_response(pages_ready, r, {t: 'pending' if pre_tasks.get(t) else 'published' for t in task_type})
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})

        # 测试已发布的页面
        pages_published_before = ['YB_22_713', 'YB_22_759', 'YB_22_816', 'YB_22_916', 'YB_22_995']
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_OPENED for t in task_type})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(pages_published_before))))
        self._assert_response(pages_published_before, r, {t: 'published_before' for t in task_type})

        # 组合测试
        all_pages = pages_un_existed + pages_un_ready + pages_ready + pages_published_before
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_UNREADY for t in task_type})
        self._set_page_status(pages_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_OPENED for t in task_type})
        r = self.parse_response(self._publish(dict(task_type=task_type, pages=','.join(all_pages))))
        self._assert_response(pages_un_existed, r, {t: 'un_existed' for t in task_type})
        self._assert_response(pages_un_ready, r, {t: 'un_ready' for t in task_type})
        self._assert_response(pages_ready, r, {t: 'pending' if pre_tasks.get(t) else 'published' for t in task_type})
        self._assert_response(pages_published_before, r, {t: 'published_before' for t in task_type})

        # 还原页面状态
        self._set_page_status(pages_un_ready, {t: TaskHandler.STATUS_READY for t in task_type})
        self._set_page_status(pages_published_before, {t: TaskHandler.STATUS_READY for t in task_type})

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
        self._publish_task('block_cut_proof')  # 测试一级任务
        self._publish_task('block_cut_review')  # 测试一级任务有前置任务的情况
        self._publish_task('text_proof.1')  # 测试二级任务
        self._publish_task(['text_proof.1', 'text_proof.2', 'text_proof.3'])  # 测试任务组合

        # 测试超大规模
        # self._publish_many_tasks('block_cut_proof', 10000)

    def _publish_file(self, task_type, txt_file, priority=1):
        body = dict(task_type=task_type, priority=priority)
        return self.fetch('/api/task/publish_file', files=dict(txt_file=txt_file), body=body)

    def test_publish_tasks_file(self):
        """ 测试发布审校任务 """
        self.add_first_user_as_admin_then_login()
        pages = ['GL_1056_5_6', 'JX_165_7_12']
        self._set_page_status(pages, {'block_cut_proof': 'ready'})
        filename = './static/upload/file2upload.txt'
        with open(filename, 'w') as f:
            for page in pages:
                f.write(page+'\n')
            f.close()

        filename = os.path.join(self._app.BASE_DIR, 'static', 'upload', 'file2upload.txt')
        self.assertTrue(os.path.exists(filename))

        r = self.parse_response(self._publish_file(task_type='block_cut_proof', txt_file=filename))
        self.assertEqual(set(r.get('published')), set(pages))

        # 任务类型有误
        r = self.parse_response(self._publish_file(task_type='error_task_type', txt_file=filename))
        self.assertIn('task_type', r['error'])
