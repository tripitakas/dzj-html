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
        tsk = self.db.task.find_one({'_id': ObjectId(task['task_id']), 'task_type': task['task_type']})
        if not tsk:
            return errors.task_un_existed
        elif tsk['picked_user_id'] != self.current_user['_id']:
            return errors.task_unauthorized_locked
        page_name = self.prop(task, 'page_name')
        if page_name and page_name != tsk.get('doc_id'):
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
        now = datetime.now()
        page_name, result, message = task.get('page_name'), task['result'], task.get('message')
        if task['status'] == 'failed' or result.get('status') == 'failed':
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
                'status': self.STATUS_FAILED, 'updated_time': now, 'result': result, 'message': message}
            })
        else:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return errors.no_object
            # ocr_text任务不允许修改切分信息
            box_changed = task['task_type'] == 'ocr_text' and is_box_changed(result, page)
            if box_changed:
                return errors.box_not_identical[0], '(%s)切分信息不一致' % box_changed
            # 更新task
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            })
            # 更新page，并释放数据锁
            ocr, ocr_col = result.get('ocr', ''), result.get('ocr_col', '')
            ocr = '|'.join(ocr) if isinstance(ocr, list) else ocr
            ocr_col = '|'.join(ocr_col) if isinstance(ocr_col, list) else ocr_col
            width = result.get('width') or page.get('width')
            height = result.get('height') or page.get('height')
            blocks = result.get('blocks') or page.get('blocks')
            columns = result.get('columns') or page.get('columns')
            chars = result.get('chars') or page.get('chars')
            self.db.page.update_one({'name': page_name}, {'$set': {
                'width': width, 'height': height, 'ocr': ocr, 'ocr_col': ocr_col,
                'chars': chars, 'blocks': blocks, 'columns': columns, 'lock.box': {}}
            })
        return True

    def submit_upload_cloud(self, task):
        """ 提交upload_cloud任务。page中包含有云端路径img_cloud_path """
        now = datetime.now()
        page_name, result, message = task.get('page_name'), task['result'], task.get('message')
        task_update = {'updated_time': now, 'result': result, 'message': message}
        if task['status'] == 'failed' or result.get('status') == 'failed':
            task_update.update({'status': self.STATUS_FAILED, 'finished_time': now})
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        else:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return errors.no_object
            task_update.update({'status': self.STATUS_FINISHED, 'finished_time': now})
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})

            page_update = dict(img_cloud_path=self.prop(task, 'result.img_cloud_path'))
            self.db.page.update_one({'name': page_name}, {'$set': page_update})
        return True

    def submit_import_image(self, task):
        """ 提交import_image任务 """
        now = datetime.now()
        result, message = task.get('result'), task.get('message')
        if task['status'] == 'failed' or result.get('status') == 'failed':
            task_update = {'status': self.STATUS_FAILED, 'updated_time': now, 'result': result, 'message': message}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        else:
            task_update = {'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})

        return True
