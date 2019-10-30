#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.helper import is_box_changed


class SubmitDataTaskApi(TaskHandler):
    def submit_one(self, task):
        _task = self.db.task.find_one({'_id': ObjectId(task['task_id']), 'task_type': task['task_type']})
        if not _task:
            return errors.task_un_existed
        if self.prop(task, 'page_name') and self.prop(task, 'page_name') != _task.get('doc_id'):
            return errors.doc_id_not_equal
        try:
            if task['task_type'] in ['ocr_box', 'ocr_text']:
                return self.submit_ocr(task)
            elif task['task_type'] == 'upload_cloud':
                return self.submit_upload_cloud(task)
            elif task['task_type'] == 'import_image':
                return self.submit_import_image(task)
        except DbError as err:
            return err

    def submit_ocr(self, task):
        """ 提交OCR任务 """
        page_name, page, now = task['page_name'], task['result'], datetime.now()
        if task['status'] == 'success':
            _page = self.db.page.find_one({'name': page_name})
            if not _page:
                return errors.no_object
            # oct_text任务不允许修改切分信息
            if task['task_type'] == 'ocr_text' and is_box_changed(page, _page):
                return errors.box_not_identical

            task_update = {'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
            page_update = dict(blocks=page.get('blocks'), columns=page.get('columns'),
                               chars=page.get('chars'), ocr=page.get('ocr'),
                               width=page.get('width') or _page.get('width'),
                               height=page.get('height') or _page.get('height'))
            self.db.page.update_one({'name': page.get('name')}, {'$set': page_update})
        else:
            task_update = {'status': self.STATUS_RETURNED, 'updated_time': now, 'returned_reason': task.get('message')}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        return True

    def submit_upload_cloud(self, task):
        """ 提交upload_cloud任务。page中包含有云端路径img_cloud_path """
        page_name, now = task['page_name'], datetime.now()
        if task['status'] == 'success':
            _page = self.db.page.find_one({'name': page_name})
            if not _page:
                return errors.no_object
            task_update = {'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
            page_update = dict(img_cloud_path=self.prop(task, 'result.img_cloud_path'))
            self.db.page.update_one({'name': page_name}, {'$set': page_update})
        else:
            task_update = {'status': self.STATUS_RETURNED, 'updated_time': now, 'returned_reason': task.get('message')}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        return True

    def submit_import_image(self, task):
        """ 提交import_image任务 """
        now = datetime.now()
        if task['status'] == 'success':
            task_update = {'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        else:
            task_update = {'status': self.STATUS_RETURNED, 'updated_time': now, 'returned_reason': task.get('message')}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        return True
