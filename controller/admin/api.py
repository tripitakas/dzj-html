#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/12/08
"""
from bson.objectid import ObjectId
from controller import validate as v
from controller.base import BaseHandler


class DeleteOplogApi(BaseHandler):
    URL = r'/api/admin/oplog/delete'

    def post(self):
        """ 删除日志"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            _ids = [self.data['_id']] if self.data.get('_id') else self.data['_ids']
            r = self.db.oplog.delete_many({'_id': {'$in': [ObjectId(i) for i in _ids]}})
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)
