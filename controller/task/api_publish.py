#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
import math
from datetime import datetime
import controller.errors as e
import controller.validate as v
from controller.base import DbError
from controller.task.base import TaskHandler


class GetReadyPagesApi(TaskHandler):
    URL = '/api/task/ready_pages/@task_type'

    def post(self, task_type):
        """ 任务管理中，获取已就绪的页面列表 """
        assert task_type in self.task_types.keys()
        try:
            data = self.get_request_data()

            condition = {'name': {}}
            if data.get('prefix'):
                condition['name'].update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                condition['name'].update({'$nin': data.get('exclude')})
            if not condition['name']:
                del condition['name']

            status_field = 'tasks.%s.status' % task_type
            condition.update({status_field: self.STATUS_READY})

            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db.page.count_documents(condition)
            pages = list(self.db.page.find(condition, {'name': 1, status_field: 1}).limit(page_size).skip(
                page_size * (page_no - 1)))
            pages, statuses = [p['name'] for p in pages], [self.prop(p, status_field) for p in pages]
            response = {'pages': pages, 'page_size': page_size, 'page_no': page_no, 'total_count': count}
            self.send_data_response(response)
        except DbError as err:
            self.send_db_error(err)


class PublishTasksApi(TaskHandler):
    MAX_IN_FIND_RECORDS = 50000  # Mongodb单次in查询的最大值
    MAX_UPDATE_RECORDS = 10000  # Mongodb单次update的最大值
    MAX_PUBLISH_RECORDS = 50000  # 用户单次发布任务最大值

    def publish_task(self, task_type, pre_tasks, sub_steps, priority, force=False, page_names=None, pages=None):
        """ 发布某个任务类型的任务。
        :param force 任务已发布时，是否重新发布
        :return 格式如下：
        { 'un_existed':[...], 'published_before':[...], 'un_ready':[...], 'published':[...], 'pending':[...],
          'publish_failed':[...], 'pending_failed':[...], 'not_published':[...] }
        """
        assert task_type in self.task_types

        # 设置pages
        log = dict()
        if page_names:
            pages = self.find_task(page_names)
            log['un_existed'] = set(page_names) - set(page['name'] for page in pages)

        # 检查未就绪的页面（状态不为STATUS_READY，也不是None）
        if pages:
            log['un_ready'], pages = self.filter_task(pages, {task_type: [self.STATUS_UNREADY, None]})

        # 不强制发布时，检查已发布的页面，包括已退回的页面（状态为OPENED\PENDING\PICKED\RETURNED\FINISHED）
        if not force and pages:
            log['published_before'], pages = self.filter_task(pages, {task_type: [
                self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED, self.STATUS_RETURNED, self.STATUS_FINISHED
            ]})

        # 发布剩下的页面
        if pages:
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                for t in pre_tasks:
                    assert t in self.task_types
                # 针对前置任务已完成的情况进行发布，设置状态为OPENED
                finished, pages = self.filter_task(pages, {t: self.STATUS_FINISHED for t in pre_tasks})
                log['published'] = self.publish_page_names(
                    finished, task_type, self.STATUS_OPENED, priority, pre_tasks, sub_steps)
                log['publish_failed'] = set(finished) - set(log['published'])

                # 针对前置任务未完成的情况（只要有一个未完成，就算未完成）进行发布，设置状态为PENDING
                unfinished, pages = self.filter_task(
                    pages, {t: [self.STATUS_FINISHED, None] for t in pre_tasks}, False, False)
                log['pending'] = self.publish_page_names(
                    unfinished, task_type, self.STATUS_PENDING, priority, pre_tasks, sub_steps)
                log['pending_failed'] = set(unfinished) - set(log['pending'])

                # 剩下的是前置任务不存在的，也发布为OPENED
                opened = self.publish_page_names(
                    [p['name'] for p in pages], task_type, self.STATUS_OPENED, priority, [], sub_steps)
                log['published'].extend(opened)

            else:
                # 针对没有前置任务的情况进行发布，设置状态为OPENED
                task_ready = [page['name'] for page in pages]
                log['published'] = self.publish_page_names(
                    task_ready, task_type, self.STATUS_OPENED, priority, pre_tasks, sub_steps)
                log['publish_failed'] = set(task_ready) - set(log['published'])
                pages = []

        # 登记未发布的页面
        if pages:
            log['not_published'] = [page['name'] for page in pages]

        return {k: v_ for k, v_ in log.items() if v_}

    def publish_page_names(self, page_names, task_type, status, priority, pre_tasks, sub_steps):
        """ 发布task_type对应的任务
        @return: 已发布的任务列表
        """
        try:
            length, total = self.MAX_UPDATE_RECORDS, len(page_names)  # 单次发布不超过10000
            lst = [page_names[length * i: length * (i + 1)] for i in range(0, math.ceil(total / length))]
            published_pages = []
            publish_time = datetime.now()
            for names in lst:
                condition = {'name': {'$in': names}, 'tasks.%s.status' % task_type: {
                    '$nin': [self.STATUS_UNREADY, None]}}
                meta = dict(status=status, priority=int(priority), steps=dict(todo=sub_steps), pre_tasks=pre_tasks,
                            publish_time=publish_time, publish_user_id=self.current_user['_id'],
                            publish_by=self.current_user['name'])
                r = self.db.page.update_many(condition, {'$set': {'tasks.%s' % task_type: meta}})
                if r.matched_count != len(names):
                    condition.update({
                        'tasks.%s.status' % task_type: status,
                        'tasks.%s.publish_time' % task_type: publish_time
                    })
                    pages = self.db.page.find(condition, {'name': 1})
                    names = [page['name'] for page in pages]
                published_pages.extend(names)
                self.add_op_log('publish_' + task_type, context='%d个任务: %s' % (len(names), ','.join(names)))
            return published_pages

        except DbError as err:
            self.send_db_error(err)

    def filter_task(self, pages, conditions, equal=True, all_satisfied=True):
        """ 根据conditions过滤pages
        :param conditions：格式为 { task_type1: status1, task_type2:status2...}，其中status可以为str或list
        :param equal: conditions中task_type对应的字段值与status是相同还是不同
        :param all_satisfied: conditions中的各项条件是全部满足还是只需要有一个满足即可
        """
        selected_page_names, left_pages = [], []
        for page in pages:
            satisfied = dict()
            for task_type, status in conditions.items():
                assert type(status) in [str, list]
                status = [status] if isinstance(status, str) else status
                task_status = self.prop(page, 'tasks.%s.status' % task_type)
                if equal:
                    satisfied[task_type] = True if task_status in status else False
                else:
                    satisfied[task_type] = True if task_status not in status else False
            # 根据参数进行筛选
            if all_satisfied:
                if len([s for s in satisfied.values() if s]) == len(conditions):
                    selected_page_names.append(page['name'])
                else:
                    left_pages.append(page)
            else:
                if len([s for s in satisfied.values() if s]) > 0:
                    selected_page_names.append(page['name'])
                else:
                    left_pages.append(page)
        return selected_page_names, left_pages

    def find_task(self, page_names):
        """ 根据task_type, page_names等参数，从数据库中查询对应的记录 """
        length, total = self.MAX_IN_FIND_RECORDS, len(page_names)  # 单次in查询不超过50000
        lst = [page_names[length * i: length * (i + 1)] for i in range(0, math.ceil(total / length))]
        pages = []
        for _page_names in lst:
            _pages = self.db.page.find({'name': {'$in': _page_names}}, self.simple_fields())
            pages.extend(list(_pages))
        return pages


class PublishTasksPageNamesApi(PublishTasksApi):
    URL = r'/api/task/publish'

    def post(self):
        """ 按照页码名称发布任务。
        @param task_type 任务类型
        @param sub_steps list，步骤
        @param pre_tasks list，前置任务
        @param pages str，待发布的页面名称
        @param pages_file file，待发布的页面文件
        @param priority str，1/2/3，数字越大优先级越高
        """
        pages_file = self.request.files.get('pages_file')
        if pages_file:
            pages_str = str(pages_file[0]['body'], encoding='utf-8')
            pre_task = self.get_body_argument('pre_tasks')
            sub_steps = self.get_body_argument('sub_steps')
            data = {
                'pages': re.sub(r"\n+", ",", pages_str),
                'task_type': self.get_body_argument('task_type', ''),
                'force': self.get_body_argument('force', ''),
                'priority': self.get_body_argument('priority', 1),
                'pre_tasks': pre_task and pre_task.split(',') or [],
                'sub_steps': sub_steps and sub_steps.split(',') or []
            }
        else:
            data = self.get_request_data()
        if 'page_names' in data and 'pages' not in data:
            data['pages'] = data.pop('page_names')
        rules = [
            (v.not_empty, 'task_type', 'force'),
            (v.not_both_empty, 'pages', 'pages_file'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
        ]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        page_names = data['pages'].split(',') if data.get('pages') else []
        if len(page_names) > self.MAX_PUBLISH_RECORDS:
            return self.send_error_response(e.task_exceed_max, message='发布任务数量超过%s' % self.MAX_PUBLISH_RECORDS)

        force = data['force'] == '1'
        log = self.publish_task(data['task_type'], data.get('pre_tasks', []), data.get('sub_steps', []),
                                data.get('priority', 1), force, page_names=page_names)
        self.send_data_response({k: v_ for k, v_ in log.items() if v_})


class PublishTasksPagePrefixApi(PublishTasksApi):
    URL = r'/api/task/publish/@page_prefix'

    def post(self, page_prefix):
        """ 按照页码前缀发布任务。
        @param task_type 任务类型
        @param pre_tasks list，前置任务
        @param page_prefix str，至少2位以上
        @param priority str，1/2/3，数字越大优先级越高
        """
        data = self.get_request_data()
        rules = [
            (v.not_empty, 'task_type', 'force'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
        ]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        force = data['force'] == '1'
        condition = {'name': {'$regex': '.*%s.*' % page_prefix, '$options': '$i'}}
        pages = self.db.page.find(condition, self.simple_fields())
        log = self.publish_task(data['task_type'], data.get('pre_tasks', []), data.get('sub_steps', []),
                                data.get('priority', 1), force, pages=pages)
        self.send_data_response({k: v_ for k, v_ in log.items() if v_})
