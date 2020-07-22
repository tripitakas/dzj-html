#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import helper as hp
from tests.testcase import APITestCase


class TestOcr(APITestCase):

    def setUp(self):
        super(TestOcr, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.reset_tasks_and_data()

    def tearDown(self):
        super(TestOcr, self).tearDown()

    def test_xiaoo_access(self):
        """ 测试小欧访问TW平台"""
        xiaoo_id = hp.prop(self._app.config, 'xiaoo.login_id')
        if not xiaoo_id:
            return
        # 管理员发布任务
        task_type = 'ocr_box'
        page_names = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
        r = self.publish_page_tasks(dict(page_names=page_names, task_type=task_type, pre_tasks=[]))
        self.assert_code(200, r)
        # 创建小欧账号
        self.add_users_by_admin([dict(email=xiaoo_id, name='小欧', password='xiaoo@123')], 'OCR加工员,单元测试用户')
        self.logout()
        # 测试小欧领取任务
        login_info = dict(login_id=xiaoo_id, password='xiaoo@123')
        r = self.fetch('/api/task/fetch_many/' + task_type, body={'data': {'size': 3, **login_info}})
        self.assert_code(200, r, msg=task_type)

    def test_ocr_task(self):
        """ 测试小欧的数据处理任务"""
        for task_type in ['ocr_box', 'ocr_text', 'upload_cloud']:
            # 发布任务
            page_names = ['QL_25_16', 'QL_25_313', 'QL_25_416', 'QL_25_733', 'YB_22_346', 'YB_22_389']
            r = self.publish_page_tasks(dict(page_names=page_names, task_type=task_type, pre_tasks=[]))
            self.assert_code(200, r)

            # 测试批量领取任务
            r = self.fetch('/api/task/fetch_many/' + task_type, body={'data': {'size': 3}})
            self.assert_code(200, r, msg=task_type)
            data = self.parse_response(r)

            # 测试批量提交任务
            tasks = []
            for task in data['data']['tasks']:
                page = self._app.db.page.find_one({'name': task['page_name']})
                page['img_cloud_path'] = 'http://cloud.tripitakas.net/abc.png'  # upload_cloud任务
                status = 'success' if page else 'failed'
                message = '' if page else '页面未找到'
                tasks.append(dict(ocr_task_id=task['task_id'], task_id=task['task_id'], task_type=task_type,
                                  page_name=task['page_name'], status=status, result=page, message=message))
            r = self.fetch('/api/task/submit/' + task_type, body={'data': {'tasks': tasks}})
            self.assert_code(200, r, msg=task_type)

            # 测试ocr_text任务不可以缺失字框
            if task_type == 'ocr_text':
                tasks[0]['result']['chars'].pop()
                r = self.fetch('/api/task/submit/' + task_type, body={'data': {'tasks': tasks}})
                self.assert_code(200, r, msg=task_type)
                d = self.parse_response(r)['data']['tasks']
                self.assertEqual('failed', d[0]['status'])

    def test_import_image(self):
        """ 测试发布导入图片任务"""
        # 发布任务
        task_type = 'import_image'
        data = dict(task_type=task_type, import_dir='/srv/test1/abc', redo='1', layout='上下一栏', source='分类')
        r = self.fetch('/api/publish/import_image', body={'data': self.set_pub_data(data)})
        self.assert_code(200, r)
        data = dict(task_type=task_type, import_dir='/srv/test2/def', redo='0', layout='上下一栏', source='分类')
        r = self.fetch('/api/publish/import_image', body={'data': self.set_pub_data(data)})
        self.assert_code(200, r)
        # 测试领取任务
        r = self.fetch('/api/task/fetch_many/' + task_type, body={'data': {'size': 100}})
        self.assert_code(200, r)
        # 测试提交任务
        task_id = self.parse_response(r)['data']['tasks'][0]['task_id']
        tasks = [dict(ocr_task_id=task_id, task_id=task_id, task_type=task_type, status='success')]
        r = self.fetch('/api/task/submit/' + task_type, body={'data': {'tasks': tasks}})
        self.assert_code(200, r, msg=task_type)
