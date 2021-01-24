#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/12/08
"""
import os
import re
from bson.objectid import ObjectId
from controller import errors as e
from controller import helper as h
from controller import validate as v
from controller.base import BaseHandler
from utils.upload_oss import upload_oss
from utils import update_exam as exam


class LogDeleteApi(BaseHandler):
    URL = r'/api/sys/(oplog|log)/delete'

    def post(self, collection):
        """删除日志"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            _ids = [self.data['_id']] if self.data.get('_id') else self.data['_ids']
            r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in _ids]}})
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class OpLogStatusApi(BaseHandler):
    URL = r'/api/sys/oplog/status/@oid'

    def post(self, oid):
        """获取运维日志状态"""
        try:
            oplog = self.db.oplog.find_one({'_id': ObjectId(oid)})
            if not oplog:
                self.send_error_response(e.no_object, message='没有找到日志')
            self.send_data_response(dict(status=oplog.get('status') or ''))

        except self.DbError as error:
            return self.send_db_error(error)


class SysUploadOssApi(BaseHandler):
    URL = r'/api/sys/upload_oss/(char|column)'

    def post(self, img_type):
        """启动上传OSS脚本"""
        try:
            r = upload_oss(img_type, True)
            if r is not True:
                self.send_error_response(r)

            # 启动脚本，生成字图
            script = 'nohup python3 %s/utils/upload_oss.py --img_type=%s >> log/upload_oss_%s.log 2>&1 &'
            script = script % (h.BASE_DIR, img_type, h.get_date_time(fmt='%Y%m%d%H%M%S'))
            # print(script)
            os.system(script)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class ResetExamUserApi(BaseHandler):
    URL = r'/api/sys/reset_exam_user'

    def post(self):
        """重置考核用户相关数据和任务"""
        try:
            user_no = None
            user_id = self.data['user_id']
            if user_id != 'all':
                user = self.db.user.find_one({'_id': ObjectId(user_id)})
                if not user:
                    return self.send_error_response(e.no_object)
                r = re.findall(r'\d+', user['name'])
                assert '考核' in user['name'] and r
                user_no = int(r[0])
            if user_no:
                exam.reset_user_data_and_tasks(self.db, user_no)
                self.send_data_response(dict(status='success'))
            else:
                script = 'nohup python3 %s/utils/update_exam.py --func=reset_user_data_and_tasks >> log/update_exam_%s.log 2>&1 &'
                script = script % (h.BASE_DIR, h.get_date_time(fmt='%Y%m%d%H%M%S'))
                print(script)
                os.system(script)
                self.send_data_response(dict(status='script'))

        except self.DbError as error:
            return self.send_db_error(error)
