#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/12/08
"""
from bson.objectid import ObjectId
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler


class LogDeleteApi(BaseHandler):
    URL = r'/api/sys/(oplog|log)/delete'

    def post(self, collection):
        """ 删除日志"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            _ids = [self.data['_id']] if self.data.get('_id') else self.data['_ids']
            r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in _ids]}})
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class OpLogStatus(BaseHandler):
    URL = r'/api/sys/oplog/status/@oid'

    def post(self, oid):
        """ 获取运维日志状态"""
        try:
            oplog = self.db.oplog.find_one({'_id': ObjectId(oid)})
            if not oplog:
                self.send_error_response(e.no_object, message='没有找到日志')
            self.send_data_response(dict(status=oplog.status))

        except self.DbError as error:
            return self.send_db_error(error)
