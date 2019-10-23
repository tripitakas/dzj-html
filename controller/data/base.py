#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据任务基类
@time: 2019/3/11
"""
import re
from datetime import datetime
from controller import validate as v
from controller.base import BaseHandler


class DataHandler(BaseHandler):
    # 数据任务定义表。
    data_tasks = {
        'ocr': {'name': 'OCR处理'},
        'upload_cloud': {'name': '上传云图'},
        'import_image': {'name': '导入图片'},
    }
    # 数据状态表
    STATUS_TODO = 'todo'
    STATUS_PICKED = 'picked'
    STATUS_FAILED = 'failed'
    STATUS_FINISHED = 'finished'

    status_names = {STATUS_TODO: '排队中', STATUS_PICKED: '进行中', STATUS_FAILED: '失败', STATUS_FINISHED: '已完成'}

    @classmethod
    def get_status_name(cls, status):
        return cls.status_names.get(status)

    def publish(self, data_task):
        data = self.get_request_data()
        data['doc_ids'] = self._get_doc_ids(data)
        rules = [(v.not_empty, 'doc_ids', 'force')]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        assert isinstance(data['doc_ids'], list)
        force = data['force'] == '1'
        log = self._publish(data['doc_ids'], force, data_task)
        return self.send_data_response({k: value for k, value in log.items() if value})

    def _publish(self, page_names, force, data_task):
        """ 发布数据任务。
        :param page_names 待发布的页面
        :param force 页面已完成时，是否重新发布
        :param data_task 更新page表的哪个字段
        :return 格式如下：{'un_existed':[...],  'finished':[...], 'published':[...]}
        """
        assert data_task in self.data_tasks

        log = dict()

        # 检查页面是否存在
        pages = list(self.db['page'].find({'name': {'$in': page_names}}))
        log['un_existed'] = set(page_names) - set([page.get('name') for page in pages])
        page_names = [page.get('name') for page in pages]

        # 去掉已完成的任务（如果不重新发布）
        if not force and page_names:
            condition = dict(status=self.STATUS_FINISHED, page_id={'$in': list(page_names)})
            log['finished'] = set(t.get('name') for t in self.db.page.find(condition, {'name': 1}))
            page_names = set(page_names) - log['finished']

        # 发布数据任务
        if page_names:
            update = dict(status=self.STATUS_TODO, create_time=datetime.now(), updated_time=datetime.now(),
                          publish_user_id=self.current_user['_id'], publish_by=self.current_user['name'])
            self.db.page.update_many({'name': {'$in': list(page_names)}}, {'$set': {'tasks.%s' % data_task: update}})
            log['published'] = page_names

        return {k: value for k, value in log.items() if value}

    def _get_doc_ids(self, data):
        """从文件或前缀中获取页面ID"""
        doc_ids = data.get('doc_ids')
        if not doc_ids:
            ids_file = self.request.files.get('ids_file')
            if ids_file:
                ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
            elif data.get('prefix'):
                condition = {'name': {'$regex': '.*%s.*' % data['prefix'], '$options': '$i'}}
                doc_ids = [doc.get('name') for doc in self.db.page.find(condition)]
        return doc_ids
