#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: OCR相关api，供小欧调用
@time: 2019/5/13
"""
import logging
from bson.objectid import ObjectId
from controller import errors as e
from controller import validate as v
from controller.task.base import TaskHandler


class FetchTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@ocr_task'

    def post(self, data_task):
        """ 批量领取小欧任务"""

        def get_tasks():
            doc_ids = [t['doc_id'] for t in tasks]
            pages = self.db.page.find({'name': {'$in': doc_ids}})
            pages = {p['name']: {k: p.get(k) for k in ['layout', 'blocks', 'columns', 'chars']} for p in pages}
            if data_task == 'ocr_box':
                # 把layout参数传过去
                for t in tasks:
                    t['params'] = dict(layout=self.prop(pages, '%s.layout' % t['doc_id']))
            if data_task == 'ocr_text':
                # 把layout/blocks/columns/chars等参数传过去
                for t in tasks:
                    t['params'] = pages.get(t['doc_id'])

            return [dict(task_id=str(t['_id']), priority=t.get('priority'), page_name=t.get('doc_id'),
                         params=t.get('params')) for t in tasks]

        try:
            size = int(self.data.get('size') or 1)
            condition = {'task_type': data_task, 'status': self.STATUS_PUBLISHED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_data_response(dict(tasks=[]))
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': dict(
                status=self.STATUS_FETCHED, picked_time=self.now(), updated_time=self.now(),
                picked_user_id=self.user_id, picked_by=self.username
            )})
            if r.matched_count:
                logging.info('%d %s tasks fetched' % (r.matched_count, data_task))
                self.send_data_response(dict(tasks=get_tasks()))

        except self.DbError as error:
            return self.send_db_error(error)


class ConfirmFetchApi(TaskHandler):
    URL = '/api/task/confirm_fetch/@ocr_task'

    def post(self, data_task):
        """ 确认批量领取任务成功"""

        try:
            rules = [(v.not_empty, 'tasks')]
            self.validate(self.data, rules)

            if self.data['tasks']:
                task_ids = [ObjectId(t['task_id']) for t in self.data['tasks']]
                self.db.task.update_many({'_id': {'$in': task_ids}}, {'$set': {'status': self.STATUS_PICKED}})
                tasks = self.db.task.find({'_id': {'$in': task_ids}}, {'doc_id': 1, 'collection': 1, 'num': 1})
                page_names = [t['doc_id'] for t in tasks if t.get('doc_id') and t.get('collection') == 'page']
                if page_names:
                    # 默认小欧任务只有一个校次
                    self.db.page.update_many({'name': {'$in': page_names}}, {'$set': {
                        'tasks.%s.%s' % (data_task, 1): self.STATUS_PICKED
                    }})
                self.send_data_response()
            else:
                self.send_error_response(e.no_object)

        except self.DbError as error:
            return self.send_db_error(error)


class SubmitTasksApi(TaskHandler):
    URL = '/api/task/submit/@ocr_task'

    def post(self, task_type):
        """ 批量提交数据任务。提交参数为tasks，格式如下：
        [{'task_type': '', 'ocr_task_id':'', 'task_id':'', 'page_name':'', 'status':'success', 'result':{}},
         {'task_type': '', 'ocr_task_id':'','task_id':'', 'page_name':'', 'status':'failed', 'message':''},]
        其中，ocr_task_id是远程任务id，task_id是本地任务id，status为success/failed，
        result是成功时的数据，message为失败时的错误信息。
        """
        try:
            rules = [(v.not_empty, 'tasks')]
            self.validate(self.data, rules)

            ret_tasks = []
            for rt in self.data['tasks']:
                r = None
                lt = self.db.task.find_one({'_id': ObjectId(rt['task_id']), 'task_type': rt['task_type']})
                if not lt:
                    r = e.task_not_existed
                elif lt['picked_user_id'] != self.user_id:
                    r = e.task_has_been_picked
                elif self.prop(rt, 'page_name') and self.prop(rt, 'page_name') != lt.get('doc_id'):
                    r = e.doc_id_not_equal
                elif task_type == 'ocr_box':
                    r = self.submit_ocr_box(rt)
                elif task_type == 'ocr_text':
                    r = self.submit_ocr_text(rt)
                elif task_type == 'upload_cloud':
                    r = self.submit_upload_cloud(rt)
                elif task_type == 'import_image':
                    self.submit_import_image(rt)

                message = '' if r in [None, True] else r
                status = 'success' if r in [None, True] else 'failed'
                ret_tasks.append(dict(ocr_task_id=rt['ocr_task_id'], task_id=rt['task_id'], status=status,
                                      page_name=rt.get('page_name'), message=message))

            self.send_data_response(dict(tasks=ret_tasks))

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def get_page_meta(task, page):
        result = task.get('result')
        width = result.get('width') or page.get('width')
        height = result.get('height') or page.get('height')
        layout = result.get('layout') or page.get('layout')
        chars = result.get('chars') or page.get('chars')
        blocks = result.get('blocks') or page.get('blocks')
        columns = result.get('columns') or page.get('columns')
        return {
            'width': width, 'height': height, 'layout': layout,
            'chars': chars, 'blocks': blocks, 'columns': columns,
        }

    @staticmethod
    def is_box_changed(page_a, page_b, ignore_none=True):
        """ 检查两个页面的切分信息是否发生了修改"""
        for field in ['blocks', 'columns', 'chars']:
            a, b = page_a.get(field), page_b.get(field)
            if ignore_none and (not a or not b):
                continue
            if len(a) != len(b):
                return field + '.len'
            for i in range(len(a)):
                for j in ['x', 'y', 'w', 'h']:
                    if abs(a[i][j] - b[i][j]) > 0.1 and (field != 'blocks' or len(a) > 1):
                        return '%s[%d] %s %f != %f' % (field, i, j, a[i][j], b[i][j])

    def submit_ocr_box(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')})
        if not page:
            return e.no_object
        update = self.get_page_meta(task, page)
        update.update({'tasks.%s.%s' % (task.get('num') or 1, task['task_type']): self.STATUS_FINISHED})
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': update})

        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_ocr_text(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')})
        if not page:
            return e.no_object
        box_changed = self.is_box_changed(task.get('result'), page)
        if box_changed:
            return e.box_not_identical[0], '(%s)切分信息不一致' % box_changed
        update = self.get_page_meta(task, page)
        update.update({'tasks.%s.%s' % (task.get('num') or 1, task['task_type']): self.STATUS_FINISHED})
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': update})

        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_upload_cloud(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')})
        if not page:
            return e.no_object
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': {
            'img_cloud_path': self.prop(task, 'result.img_cloud_path'),
            'tasks.%s.%s' % (task.get('num') or 1, task['task_type']): self.STATUS_FINISHED
        }})
        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_import_image(self, task):
        """ 提交import_image任务"""
        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})
