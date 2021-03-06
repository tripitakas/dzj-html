#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: OCR相关api，供小欧调用
@time: 2019/5/13
"""
import logging
from bson.objectid import ObjectId
from controller import errors as e
from controller import helper as hp
from controller import validate as v
from controller.task.base import TaskHandler
from controller.page.base import PageHandler


class FetchTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@ocr_task'

    def post(self, data_task):
        """批量领取小欧任务"""

        def get_tasks():
            doc_ids = [t['doc_id'] for t in tasks]
            pages = self.db.page.find({'name': {'$in': doc_ids}})
            fields = ['layout', 'width', 'height', 'blocks', 'columns', 'chars']
            pages = {p['name']: {k: p.get(k) for k in fields} for p in pages}
            if data_task == 'ocr_box':
                # 把layout参数传过去
                for t in tasks:
                    t['params'] = dict(layout=self.prop(pages, '%s.layout' % t['doc_id']))
            if data_task == 'ocr_text':
                # 把layout/width/height/blocks/columns/chars等参数传过去
                for t in tasks:
                    page = pages.get(t['doc_id'])
                    PageHandler.pack_cut_boxes(page, log=False, sub_columns=True)
                    t['params'] = page
            return [dict(task_id=str(t['_id']), num=t.get('num'), priority=t.get('priority'),
                         page_name=t.get('doc_id'), params=t.get('params')) for t in tasks]

        try:
            size = int(self.data.get('size') or 1)
            p = {f: 1 for f in ['num', 'priority', 'doc_id', 'params']}
            tasks = list(self.db.task.find({'task_type': data_task, 'status': self.STATUS_PUBLISHED}, p).limit(size))
            if not tasks:
                tasks = list(self.db.task.find({'task_type': data_task, 'status': self.STATUS_FETCHED}, p).limit(size))
                if not tasks:
                    self.send_data_response(dict(tasks=[]))
            tasks2send = get_tasks()
            # logging.info(tasks2send)
            cond = {'_id': {'$in': [ObjectId(t['task_id']) for t in tasks2send]}}
            r = self.db.task.update_many(cond, {'$set': dict(
                status=self.STATUS_FETCHED, picked_time=self.now(), updated_time=self.now(),
                picked_user_id=self.user_id, picked_by=self.username
            )})
            if r.matched_count:
                logging.info('%d %s tasks fetched' % (r.matched_count, data_task))
                self.send_data_response(dict(tasks=tasks2send))

        except self.DbError as error:
            return self.send_db_error(error)


class ConfirmFetchApi(TaskHandler):
    URL = '/api/task/confirm_fetch/@ocr_task'

    def post(self, data_task):
        """确认批量领取任务成功"""

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


class SubmitTasksApi(PageHandler):
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
                lt = self.db.task.find_one({'_id': ObjectId(rt['task_id'])})
                if not lt:
                    r = e.task_not_existed
                elif rt['task_type'] != lt['task_type']:
                    r = e.task_type_error
                elif self.prop(rt, 'page_name') and self.prop(rt, 'page_name') != lt.get('doc_id'):
                    r = e.doc_id_not_equal
                elif self.prop(rt, 'result.status') == 'failed':  # 小欧任务失败
                    self.db.task.update_one({'_id': lt['_id']}, {'$set': {
                        'status': 'failed', 'result': rt.get('result')
                    }})
                    r = True
                elif task_type == 'ocr_box':
                    r = self.submit_ocr_box(rt)
                elif task_type == 'ocr_text':
                    r = self.submit_ocr_text(rt)
                elif task_type == 'upload_cloud':
                    r = self.submit_upload_cloud(rt)
                elif task_type == 'import_image':
                    self.submit_import_image(rt)

                message = r if isinstance(r, tuple) else ''
                status = 'failed' if isinstance(r, tuple) else 'success'
                ret_tasks.append(dict(ocr_task_id=rt['ocr_task_id'], task_id=rt['task_id'], status=status,
                                      page_name=rt.get('page_name'), message=message))
                if status == 'failed':
                    self.db.task.update_one({'_id': ObjectId(rt['task_id'])}, {'$set': {
                        'status': status, 'result': rt.get('result'), 'message': message
                    }})

            self.send_data_response(dict(tasks=ret_tasks))

        except self.DbError as error:
            return self.send_db_error(error)

    def submit_ocr_box(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')}, {'name': 1})
        if not page:
            return e.no_object

        fields = ['width', 'height', 'layout']
        update = {k: self.prop(task, 'result.' + k) for k in fields if self.prop(task, 'result.' + k)}
        # ocr_box任务将覆盖page已有的栏框、列框和字框数据
        update.update({k: self.prop(task, 'result.' + k) for k in ['blocks', 'columns', 'chars']})
        update['tasks.%s.%s' % (task['task_type'], task.get('num') or 1)] = self.STATUS_FINISHED
        update['page_code'] = hp.align_code(page['name'])
        update['create_time'] = self.now()
        # 将列文本适配至字框
        try:
            mis_len = self.apply_ocr_col(update)
            update['txt_match.ocr_col.mis_len'] = mis_len
        except Exception as err:
            update['apply_error'] = str(err)
        # 更新页数据和相关任务
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': update})
        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_ocr_text(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')})
        if not page:
            return e.no_object
        # 更新列框文本
        columns1 = {c['cid']: c for c in self.prop(task, 'result.columns') if c.get('cid')}
        for c in page['columns']:
            oc = columns1.get(c['cid'])
            if not oc:  # 报错以便通过失败的任务及时发现问题
                return e.box_not_identical[0], '列框（cid：%s）缺失' % c['cid']
            c.update({k: oc.get(k) or c.get(k) for k in ['lc', 'ocr_txt']})
            if c.get('sub_columns'):
                if not oc.get('sub_columns'):
                    return e.box_not_identical[0], '列框（cid：%s）的子列缺失' % c['cid']
                if len(c['sub_columns']) != len(oc['sub_columns']):
                    return e.box_not_identical[0], '列框（cid：%s）的子列数量不一致' % c['cid']
                for i, sub in enumerate(c['sub_columns']):
                    o_sub = oc['sub_columns'][i]
                    sub.update({k: o_sub.get(k) or sub.get(k) for k in ['lc', 'ocr_txt']})
        # 更新字框文本
        chars1 = {c['cid']: c for c in self.prop(task, 'result.chars') if c.get('cid')}
        for c in page['chars']:
            oc = chars1.get(c['cid'])
            if not oc:
                return e.box_not_identical[0], '字框（cid：%s）缺失' % c['cid']
            c.update({k: oc.get(k) or c.get(k) for k in ['cc', 'alternatives', 'ocr_txt']})
        # 将列文本适配至字框
        try:
            mis_len = self.apply_ocr_col(page)
            page['txt_match.ocr_col.mis_len'] = mis_len
        except Exception as err:
            page['apply_error'] = str(err)
        # 更新页数据和相关任务
        update = {f: page[f] for f in ['chars', 'columns', 'txt_match.ocr_col.mis_len', 'apply_error'] if page.get(f)}
        update['tasks.%s.%s' % (task['task_type'], task.get('num') or 1)] = self.STATUS_FINISHED
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': update})
        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_upload_cloud(self, task):
        page = self.db.page.find_one({'name': task.get('page_name')}, {'name': 1})
        if not page:
            return e.no_object
        self.db.page.update_one({'name': task.get('page_name')}, {'$set': {
            'tasks.%s.%s' % (task['task_type'], task.get('num') or 1): self.STATUS_FINISHED
        }})

        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})

    def submit_import_image(self, task):
        """提交import_image任务"""
        self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
            'result': task.get('result'), 'message': task.get('message'),
            'status': self.STATUS_FINISHED, 'finished_time': self.now(),
        }})
