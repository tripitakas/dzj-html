#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors as e
from controller.helper import get_url_param
from controller.task.base import TaskHandler


class PageTaskHandler(TaskHandler):
    step2box = dict(chars='char', columns='column', blocks='block', orders='char')

    def __init__(self, application, request, **kwargs):
        super(TaskHandler, self).__init__(application, request, **kwargs)
        self.page = self.box_type = self.boxes = None

    def prepare(self):
        super().prepare()
        if self.error:
            return
        self.box_type = self.step2box.get(self.steps['current'])
        if self.task:
            self.page = self.db.page.find_one({self.task['id_name']: self.task['doc_id']})
            if not self.page:
                self.error = e.no_object
                return self.send_error_response(e.no_object, message='页面%s不存在' % self.task['doc_id'])
            self.boxes = self.page.get(self.box_type + 's')

    def get_task(self, task_id):
        """ 根据task_id/to以及相关查询条件，获取页任务。重载父函数"""
        # 查找当前任务
        cur_task = self.db.task.find_one({'_id': ObjectId(task_id)})
        if not cur_task:
            error = e.task_not_existed[0], '没有找到任务%s' % task_id
            return None, error
        # 设置检索参数
        to = self.get_query_argument('to', '')
        condition = self.get_search_condition(self.request.query)[0]
        if to == 'next':
            condition.update({'_id': {'$lt': ObjectId(task_id)}})
        elif to == 'prev':
            condition.update({'_id': {'$gt': ObjectId(task_id)}})
        else:
            condition.update({'_id': ObjectId(task_id)})
        # 检查目标任务
        to_task = self.db.task.find_one(condition, sort=[('_id', 1 if to == 'prev' else -1)])
        if not to_task:
            error = e.task_not_existed[0], '没有找到任务%s的%s任务' % (task_id, '前一个' if to == 'prev' else '后一个')
            return None, error
        elif cur_task['task_type'] != to_task['task_type']:
            query = re.sub('[?&]to=(prev|next)', '', self.request.query)
            url = '/task/browse/%s/%s?' % (to_task['task_type'], to_task['_id']) + query
            self.redirect(url.rstrip('?'))
            return None, e.task_type_error
        return to_task, None

    def page_title(self):
        return '%s-%s' % (self.task_name(), self.page.get('name') or '')

    def task_name(self):
        return self.get_task_name(self.task_type) or '切分'

    def step_name(self):
        return self.get_step_name(self.steps["current"]) or ''

    @staticmethod
    def get_search_condition(request_query):
        """ 获取页任务的查询条件"""
        condition, params = dict(collection='page'), dict()
        for field in ['batch', 'task_type', 'doc_id', 'status', 'priority', 'remark']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        picked_user_id = get_url_param('picked_user_id', request_query)
        if picked_user_id:
            params['picked_user_id'] = picked_user_id
            condition.update({'picked_user_id': ObjectId(picked_user_id)})
        publish_start = get_url_param('publish_start', request_query)
        if publish_start:
            params['publish_start'] = publish_start
            condition['publish_time'] = {'$gt': datetime.strptime(publish_start, '%Y-%m-%d %H:%M:%S')}
        publish_end = get_url_param('publish_end', request_query)
        if publish_end:
            params['publish_end'] = publish_end
            condition['publish_time'] = condition.get('publish_time') or {}
            condition['publish_time'].update({'$lt': datetime.strptime(publish_end, '%Y-%m-%d %H:%M:%S')})
        picked_start = get_url_param('picked_start', request_query)
        if picked_start:
            params['picked_start'] = picked_start
            condition['picked_time'] = {'$gt': datetime.strptime(picked_start, '%Y-%m-%d %H:%M:%S')}
        picked_end = get_url_param('picked_end', request_query)
        if picked_end:
            params['picked_end'] = picked_end
            condition['picked_time'] = condition.get('picked_time') or {}
            condition['picked_time'].update({'$lt': datetime.strptime(picked_end, '%Y-%m-%d %H:%M:%S')})
        finished_start = get_url_param('finished_start', request_query)
        if finished_start:
            params['finished_start'] = finished_start
            condition['picked_time'] = {'$gt': datetime.strptime(finished_start, '%Y-%m-%d %H:%M:%S')}
        finished_end = get_url_param('finished_end', request_query)
        if finished_end:
            params['finished_end'] = finished_end
            condition['finished_time'] = condition.get('finished_time') or {}
            condition['finished_time'].update({'$lt': datetime.strptime(finished_end, '%Y-%m-%d %H:%M:%S')})
        return condition, params
