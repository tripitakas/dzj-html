#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
import controller.errors as e
import controller.validate as v
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.task.publish import PublishTasksHandler


class GetReadyTasksApi(TaskHandler):
    URL = '/api/task/ready/@task_type'

    def post(self, task_type):
        """ 查找任务对应的数据表collection，获取数据已就绪的任务列表 """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()

            task_meta = self.task_types[task_type]
            collection, id_name = task_meta['data']['collection'], task_meta['data']['id']
            id_value = {}
            if data.get('prefix'):
                id_value.update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                id_value.update({'$nin': data.get('exclude')})
            condition = {id_name: id_value} if id_value else {}
            condition.update({'status': self.STATUS_READY})

            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db.page.count_documents(condition)
            docs = self.db.page.find(condition).limit(page_size).skip(page_size * (page_no - 1))
            response = {'docs': [d[id_name] for d in list(docs)], 'page_size': page_size,
                        'page_no': page_no, 'total_count': count}
            self.send_data_response(response)
        except DbError as err:
            self.send_db_error(err)


class PublishTasksByIdsApi(PublishTasksHandler):
    URL = r'/api/task/publish_by_ids'

    def post(self):
        """ 根据数据id发布任务。
        @param task_type 任务类型
        @param sub_steps list，步骤
        @param pre_tasks list，前置任务
        @param ids str，待发布的任务名称
        @param priority str，1/2/3，数字越大优先级越高
        """
        data = self.get_request_data()
        rules = [
            (v.not_empty, 'ids', 'task_type', 'priority'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
        ]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        try:
            ids = data['ids'].split(',') if data.get('ids') else []
            if len(ids) > self.MAX_PUBLISH_RECORDS:
                return self.send_error_response(e.task_exceed_max, message='任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS)

            log = self.publish_task(data['task_type'], data.get('pre_tasks', []), data.get('steps', []),
                                    data['priority'], ids=ids)
            self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as err:
            self.send_db_error(err)


class PublishTasksByFileApi(PublishTasksByIdsApi):
    URL = r'/api/task/publish_by_file'

    def get_request_data(self):
        ids_file = self.request.files.get('ids_file')
        ids_str = str(ids_file[0]['body'], encoding='utf-8')
        pre_task = self.get_body_argument('pre_tasks', '')
        steps = self.get_body_argument('steps', '')
        data = {
            'ids': re.sub(r'\n+', ',', ids_str),
            'task_type': self.get_body_argument('task_type', ''),
            'priority': self.get_body_argument('priority', 1),
            'pre_tasks': pre_task and pre_task.split(',') or [],
            'sub_steps': steps and steps.split(',') or []
        }
        return data

    def post(self):
        """ 根据数据文件发布任务"""
        super().post()


class PublishTasksPagePrefixApi(PublishTasksByIdsApi):
    URL = r'/api/task/publish_by_prefix'

    def get_request_data(self):
        # 根据prefix，查找数据已就绪的记录
        data = super().get_request_data()
        if not data.get('prefix') or not data.get('prefix'):
            return data
        d = self.task_types[data['task_type']]['data']
        collection, id_name, input_field = d['collection'], d['id'], d['input_field']
        condition = {id_name: {'$regex': '.*%s.*' % data['prefix'], '$options': '$i'},
                     input_field: {"$nin": [None, '']}}
        docs = self.db[collection].find(condition)
        ids = [doc.get(id_name) for doc in docs]
        data.update({'ids': ids})
        return data

    def post(self):
        """ 按照前缀发布任务 """
        super().post()
