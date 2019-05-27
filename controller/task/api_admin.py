#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import math
from datetime import datetime
import controller.errors as e
import controller.validate as v
from controller.base import DbError
from controller.task.base import TaskHandler


class PublishTasksApi(TaskHandler):
    URL = r'/api/task/publish'

    def post(self):
        """ 发布任务。
        @param task_type str或list，如text_review/text_proof.1或[text_proof.1, text_proof.2, text_proof.3]
        @param pages str，待发布的页面名称
        @param priority str，1/2/3
        """
        data = self.get_request_data()
        rules = [
            (v.not_empty, 'task_type', 'pages'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', self.all_task_types())
        ]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        task_type = data.get('task_type')
        task_type = [task_type] if isinstance(task_type, str) else task_type
        priority = data.get('priority') or 1
        page_names = data['pages'].split(',') if data.get('pages') else []

        if len(page_names) > self.MAX_PUBLISH_RECORDS:
            return self.send_error_response(e.task_exceed_max, message='任务数量超过%s' % self.MAX_PUBLISH_RECORDS)

        if len(task_type) == 1:
            log = self.publish_task(page_names, task_type[0], priority)
        else:
            log = {t: self.publish_task(page_names, t, priority) for t in task_type}
        self.send_data_response({k: v for k, v in log.items() if v})

    def publish_task(self, page_names, task_type, priority):
        """
        发布某个任务类型的任务。
        :param task_type 格式为str，如text_review/text_proof.1
        :return {'un_existed':[...], 'published_before':[...], 'un_ready':[...], 'published':[...], 'pending':[...],
                 'publish_failed':[...], 'pending_failed':[...], 'not_published':[...]}
        """
        # 检查数据库中不存在的page_names
        log = dict()
        pages = self.find_task(task_type, page_names)
        existed = [page['name'] for page in pages]
        log['un_existed'] = [i for i in page_names if i not in existed]

        # 检查已发布的page_names（状态为OPENED\PENDING\PICKED\RETURNED\FINISHED）
        if pages:
            log['published_before'] = self.filter_task(pages, {task_type: [
                self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED, self.STATUS_RETURNED, self.STATUS_FINISHED
            ]})
            pages = [page for page in pages if page['name'] not in log['published_before']]

        # 检查未就绪的page_names（状态不为STATUS_READY）
        if pages:
            task_ready = self.filter_task(pages, {task_type: self.STATUS_READY})
            log['un_ready'] = [page['name'] for page in pages if page['name'] not in task_ready]
            pages = [page for page in pages if page['name'] in task_ready]

        # 针对已就绪的page_names（状态为READY），进行发布任务
        if pages:
            pre_tasks = self.pre_tasks().get(task_type)
            if pre_tasks:
                # 针对前置任务已完成的情况进行发布，设置状态为OPENED
                pre_finish = self.filter_task(pages, {t: self.STATUS_FINISHED for t in pre_tasks})
                log['published'] = self._publish_task(pre_finish, task_type, self.STATUS_OPENED, priority)
                log['publish_failed'] = [i for i in pre_finish if i not in log['published']]
                pages = [page for page in pages if page['name'] not in log['published'] + log['publish_failed']]

                # 针对前置任务未完成的情况（只要有一个未完成，就算未完成）进行发布，设置状态为PENDING
                pre_unfinished = self.filter_task(pages, {t: self.STATUS_FINISHED for t in pre_tasks}, False, False)
                log['pending'] = self._publish_task(pre_unfinished, task_type, self.STATUS_PENDING, priority)
                log['pending_failed'] = [i for i in pre_unfinished if i not in log['pending']]
                pages = [page for page in pages if page['name'] not in log['pending'] + log['pending_failed']]
            else:
                # 针对没有前置任务的情况进行发布，设置状态为OPENED
                task_ready = [page['name'] for page in pages]
                log['published'] = self._publish_task(task_ready, task_type, self.STATUS_OPENED, priority)
                pages = [page for page in pages if page['name'] not in log['published']]

        # 其余page_names，设置为未发布
        if pages:
            log['not_published'] = [page['name'] for page in pages]

        return {k: v for k, v in log.items() if v}

    def _publish_task(self, page_names, task_type, status, priority):
        """
        从page_names中，发布task_type对应的任务
        :return: 已发布的任务列表
        """
        assert task_type in self.all_task_types()
        try:
            start, length, total = 0, self.MAX_UPDATE_RECORDS, len(page_names)  # 单次发布不超过10000
            lst = [page_names[length * i: length * (i + 1)] for i in range(0, math.ceil(total / length))]
            published_pages = []
            for _page_names in lst:
                condition = {'name': {'$in': _page_names}}
                r = self.db.page.update_many(condition, {'$set': {
                    '%s.status' % task_type: status,
                    '%s.priority' % task_type: priority,
                    '%s.publish_time' % task_type: datetime.now(),
                    '%s.publish_user_id' % task_type: self.current_user['_id'],
                    '%s.publish_by' % task_type: self.current_user['name'],
                }})
                if r.matched_count == len(_page_names):
                    published_pages.extend(_page_names)
                    self.add_op_log('publish_' + task_type, file_id='', context=','.join(_page_names))
                else:
                    condition.update({'%s.status' % task_type: status})
                    pages = self.db.page.find(condition, {'name': 1})
                    _published_pages = [page['name'] for page in list(pages)]
                    published_pages.extend(_published_pages)
                    self.add_op_log('publish_' + task_type, file_id='', context=','.join(_published_pages))
            return published_pages

        except DbError as err:
            self.send_db_error(err)

    def filter_task(self, pages, conditions, equal=True, all_satisfied=True):
        """
        根据conditions过滤pages
        :param conditions：格式为 { task_type1: status1, task_type2:status2...}，其中status可以为str或list
        :param equal: task_type对应的字段值是否为status
        :param all_satisfied: conditions中的各项条件是否全部满足
        """
        _pages = []
        for page in pages:
            satisfied = dict()
            for task_type, status in conditions.items():
                assert type(status) in [str, list]
                status = [status] if isinstance(status, str) else status
                task_status = self.get_obj_property(page, '%s.status' % task_type)
                if equal:
                    satisfied[task_type] = True if task_status in status else False
                else:
                    satisfied[task_type] = True if task_status not in status else False
            if all_satisfied:
                if len([s for s in satisfied.values() if s]) == len(conditions):
                    _pages.append(page['name'])
            else:
                if len([s for s in satisfied.values() if s]) > 0:
                    _pages.append(page['name'])
        return _pages

    def find_task(self, task_type, page_names):
        """根据task_type, page_names等参数，从数据库中查询对应的记录"""
        start, length, total = 0, self.MAX_IN_FIND_RECORDS, len(page_names)  # 单次查询不超过50000
        lst = [page_names[length * i: length * (i + 1)] for i in range(0, math.ceil(total / length))]
        pages = []
        for _page_names in lst:
            fields = ['name', task_type] + self.pre_tasks().get(task_type, [])
            _pages = self.db.page.find({'name': {'$in': _page_names}}, {field: 1 for field in fields})
            pages.extend(list(_pages))
        return pages

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