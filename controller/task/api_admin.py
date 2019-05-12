#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
from datetime import datetime
from controller.base import DbError
from controller.task.base import TaskHandler


class PublishTasksApi(TaskHandler):
    URL = r'/api/task/publish/@task_type'

    def post(self, task_type):
        """
        发布某个任务类型的任务。
        :param task_type 任务类型。如text_review/text_proof/text_proof.1。如果task_type有子任务，则检查子任务。
        :return {'not_existed':[...], 'not_ready':[...], 'published_before':[...], 'pending':[...],
                'published':[...], 'not_published':[...]}
        """
        assert task_type in self.all_task_types()
        data = self.get_request_data()
        priority = data.get('priority', '低')
        assert priority in '高中低'
        page_names = data['pages'].split(',') if data.get('pages') else []
        log = dict()

        # 检查不存在的任务
        if page_names:
            pages = self.db.page.find({'name': {'$in': page_names}}, {'name': 1})
            existed = [page['name'] for page in list(pages)]
            log['not_existed'] = [i for i in page_names if i not in existed]
            page_names = existed

        # 检查未就绪的任务（状态为UNREADY）
        if page_names:
            log['not_ready'] = self.find_tasks_from_pages(page_names, task_type, self.STATUS_UNREADY)
            page_names = [i for i in page_names if i not in log['not_ready']]

        # 检查已发布的任务（状态为OPENED\PENDING\PICKED\RETURNED\FINISHED）
        if page_names:
            log['published_before'] = self.find_tasks_from_pages(page_names, task_type, [
                self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED, self.STATUS_RETURNED, self.STATUS_FINISHED
            ])
            page_names = [i for i in page_names if i not in log['published_before']]

        """准备发布任务"""
        if page_names:
            pre_tasks = self.pre_tasks().get(task_type)
            if pre_tasks:
                # 针对前置任务未完成的情况进行发布，状态为PENDING
                condition = self.get_status_condition(task_type, self.STATUS_READY)
                condition.update({'%s.status' % t: {"$ne": self.STATUS_FINISHED} for t in pre_tasks})
                log['pending'] = self.publish_task(page_names, condition, task_type, self.STATUS_PENDING, priority)
                page_names = [i for i in page_names if i not in log['pending']]

                # 针对前置任务已完成的情况进行发布，状态为OPENED
                condition = self.get_status_condition(task_type, self.STATUS_READY)
                condition.update({'%s.status' % t: self.STATUS_FINISHED for t in pre_tasks})
                log['published'] = self.publish_task(page_names, condition, task_type, self.STATUS_PENDING, priority)
                page_names = [i for i in page_names if i not in log['published']]
            else:
                # 针对没有前置任务的情况进行发布，状态为OPENED
                condition = self.get_status_condition(task_type, self.STATUS_READY)
                log['published'] = self.publish_task(page_names, condition, task_type, self.STATUS_OPENED, priority)
                page_names = [i for i in page_names if i not in log['published']]

        # 剩下的page_names，设置为未发布
        if page_names:
            log['not_published'] = page_names

        self.send_data_response(log)

    def publish_task(self, page_names, condition, task_type, status, priority):
        """从page_names中发布指定condition的任务，发布时设置好对应的task_type, status, priority等参数"""
        try:
            condition.update({'name': {'$in': page_names}})
            pages = self.db.page.find(condition, {'name': 1})
            if not pages:
                return []

            page_names = [page['name'] for page in list(pages)]
            condition.update({'name': {'$in': page_names}})
            update_value = {
                '%s.priority' % task_type: priority,
                '%s.publish_time' % task_type: datetime.now(),
                '%s.publish_user_id' % task_type: self.current_user['_id'],
                '%s.publish_by' % task_type: self.current_user['name'],
            }
            update_value.update(self.get_status_update(task_type, status))
            r = self.db.page.update_many(condition, {'$set': update_value})
            if r.modified_count:
                self.add_op_log('publish_' + task_type, file_id='', context=','.join(page_names))

            return page_names

        except DbError as e:
            self.send_db_error(e)

    def find_tasks_from_pages(self, page_names, task_type, status):
        """根据task_type, status参数，从page_names中查找存在的记录"""
        condition = {'name': {'$in': page_names}}
        condition.update(self.get_status_condition(task_type, status))
        pages = self.db.page.find(condition, {'name': 1})
        return [page['name'] for page in list(pages)]

    @staticmethod
    def get_status_condition(task_type, status):
        """根据是否有子任务，设置字段status的值"""
        assert type(status) in [str, list]
        sub_tasks = TaskHandler.get_sub_tasks(task_type)
        status = {"$in": status} if isinstance(status, list) else status
        if sub_tasks:
            condition = {'%s.%s.status' % (task_type, t): status for t in sub_tasks}
        else:
            condition = {'%s.status' % task_type: status}
        return condition

    @staticmethod
    def get_status_update(task_type, status):
        """根据是否有子任务，设置update"""
        assert isinstance(status, str)
        sub_tasks = TaskHandler.get_sub_tasks(task_type)
        if sub_tasks:
            update = {'%s.%s.status' % (task_type, t): status for t in sub_tasks}
        else:
            update = {'%s.status' % task_type: status}
        return update
