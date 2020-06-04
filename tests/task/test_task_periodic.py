#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tests.users as u
from tests.task.config import page_names
from tests.testcase import APITestCase
from datetime import datetime, timedelta
from periodic.statistic import statistic_tasks
from controller.helper import prop
from controller.task.base import TaskHandler as Th
from periodic.release_lock import release_timeout_lock
from periodic.republish_task import republish_timeout_tasks


class TestPeriodicTask(APITestCase):
    def setUp(self):
        super(TestPeriodicTask, self).setUp()
        self.add_first_user_as_admin_then_login()
        self.add_users_by_admin(
            [dict(email=r[0], name=r[2], password=r[1]) for r in [u.expert1]],
            '切分专家,文字专家'
        )

    def get_data_lock(self, task_type, page_name):
        page = self._app.db.page.find_one({'name': page_name})
        shared_field = Th.get_shared_field(task_type)
        return Th.prop(page, 'lock.%s' % shared_field)

    def test_republish_timeout_task(self):
        self.reset_tasks_and_data()
        # 发布任务，前置任务为空
        r = self.publish_page_tasks(dict(task_type='cut_proof', doc_ids=page_names, pre_tasks=[]))
        self.assert_code(200, r)

        # 领取任务
        self.login(u.expert1[0], u.expert1[1])
        task = self._app.db.task.find_one({'task_type': 'cut_proof', 'doc_id': page_names[0]})
        r = self.fetch('/api/task/pick/cut_proof', body={'data': {'task_id': task['_id']}})
        self.assertEqual(page_names[0], self.parse_response(r).get('doc_id'))
        task = self._app.db.task.find_one({'_id': task['_id']})
        self.assertEqual(task['picked_by'], u.expert1[2])

        # 修改发布时间
        update = {'picked_time': datetime.now() - timedelta(days=3)}
        self._app.db.task.update_one({'_id': task['_id']}, {'$set': update})

        # 测试自动回收任务
        republish_timeout_tasks(self._app.db, timeout_days=1, once_break=True)
        task = self._app.db.task.find_one({'_id': task['_id']})
        self.assertEqual(task['status'], Th.STATUS_PUBLISHED)

    def test_release_timeout_lock(self):
        # 设置数据锁时间
        update = {'lock.box': {'is_temp': True, 'locked_time': datetime.now() - timedelta(hours=6)}}
        self._app.db.page.update_one({'name': page_names[0]}, {'$set': update})

        # 测试自动释放数据锁
        release_timeout_lock(self._app.db, timeout_hours=2, once_break=True)

        page = self._app.db.page.find_one({'name': page_names[0]})
        self.assertIsNone(prop(page, 'lock.box.locked_time'))

    def test_statistic_task(self):
        self.reset_tasks_and_data()
        self._app.db.statistic.delete_many({})
        user = self._app.db.user.find_one({'email': u.expert1[0]})

        # 发布任务，前置任务为空
        r = self.publish_page_tasks(dict(task_type='cut_proof', doc_ids=page_names, pre_tasks=[]))
        self.assert_code(200, r)

        # 领取任务
        self.login(u.expert1[0], u.expert1[1])
        task1 = self._app.db.task.find_one({'task_type': 'cut_proof', 'doc_id': page_names[0]})
        r = self.fetch('/api/task/pick/cut_proof', body={'data': {'task_id': task1['_id']}})
        self.assertEqual(page_names[0], self.parse_response(r).get('doc_id'))

        # 完成任务
        update = {'status': 'finished', 'finished_time': datetime.now() - timedelta(days=3)}
        self._app.db.task.update_one({'_id': task1['_id']}, {'$set': update})

        # 领取任务
        self.login(u.expert1[0], u.expert1[1])
        task2 = self._app.db.task.find_one({'task_type': 'cut_proof', 'doc_id': page_names[1]})
        r = self.fetch('/api/task/pick/cut_proof', body={'data': {'task_id': task2['_id']}})
        self.assertEqual(page_names[1], self.parse_response(r).get('doc_id'))

        # 完成任务
        update = {'status': 'finished', 'finished_time': datetime.now() - timedelta(days=3)}
        self._app.db.task.update_one({'_id': task2['_id']}, {'$set': update})

        # 统计数据
        statistic_tasks(self._app.db, once_break=True)

        # 测试用户任务数量为1
        r = self._app.db.statistic.find_one({})
        self.assertEqual(r['user_id'], user['_id'])
        self.assertEqual(r['count'], 2)
