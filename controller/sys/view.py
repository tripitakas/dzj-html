#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/12/08
"""
import re
import os
import inspect
from os import path
from glob2 import glob
from operator import itemgetter
from bson.objectid import ObjectId
from .model import Oplog, Log
from controller import helper as h
from controller import errors as e
from controller.base import BaseHandler
from controller.auth import get_route_roles


class SysScriptHandler(BaseHandler):
    URL = '/sys/script'

    def get(self):
        """ 系统脚本"""
        try:
            tripitakas = ['所有'] + self.db.tripitaka.find().distinct('tripitaka_code')
            self.render('sys_script.html', tripitakas=tripitakas)

        except Exception as error:
            return self.send_db_error(error)


class SysLogListHandler(BaseHandler, Log):
    URL = '/sys/log'

    page_title = '操作日志'
    info_fields = ['target_id', 'content']
    update_fields = ['target_id', 'content']
    search_fields = ['op_type', 'username', 'remark']
    table_fields = ['op_type', 'target_id', 'content', 'remark', 'username', 'create_time']
    operations = [{'operation': 'bat-remove', 'label': '批量删除'}]
    img_operations = []
    actions = [{'action': 'btn-view', 'label': '查看'}]

    @classmethod
    def format_value(cls, value, key=None, doc=None):
        if key == 'op_type':
            return cls.get_type_name(value)
        if key == 'content' and value:
            value, size = str(value), 80
            return '%s%s' % (value[:size], '...' if len(value) > size else '')
        if key == 'target_id' and value:
            if isinstance(value, list) and len(value) > 10:
                value = value[:10] + ['...']
        return h.format_value(value, key, doc)

    def get(self):
        """ 操作日志"""
        try:
            kwargs = self.get_template_kwargs()
            value = h.get_url_param('op_type', self.request.uri)
            condition = {'op_type': value} if value else {}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-_id')
            self.render('sys_log.html', docs=docs, pager=pager, q=q, order=order,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class SysLogHandler(BaseHandler, Log):
    URL = '/sys/log/@oid'

    def get(self, oid):
        """ 查看操作日志"""
        try:
            log = self.db.log.find_one({'_id': ObjectId(oid)})
            if not log:
                self.send_error_response(e.no_object, message='日志不存在')
            self.render('sys_log.html', log=log)

        except Exception as error:
            return self.send_db_error(error)


class SysUploadOssHandler(BaseHandler, Log):
    URL = '/sys/upload_oss'

    def get(self):
        """ 上传图片至OSS"""
        try:
            char_names, column_names = [], []
            img_root = path.join(h.BASE_DIR, 'static', 'img')
            char_count = sum([len(x) for _, _, x in os.walk(path.join(img_root, 'chars'))])
            column_count = sum([len(x) for _, _, x in os.walk(path.join(img_root, 'columns'))])
            for root, dirs, files in os.walk(path.join(img_root, 'chars')):
                if len(char_names) < 100:
                    char_names.extend([path.basename(fn) for fn in files if fn.endswith('.jpg')])
                else:
                    break
            for root, dirs, files in os.walk(path.join(img_root, 'columns')):
                if len(column_names) < 100:
                    column_names.extend([path.basename(fn) for fn in files if fn.endswith('.jpg')])
                else:
                    break
            self.render('sys_upload_oss.html', char_count=char_count, char_names=char_names[:100],
                        column_count=column_count, column_names=column_names[:100])

        except Exception as error:
            return self.send_db_error(error)


class SysOplogListHandler(BaseHandler, Oplog):

    URL = '/sys/oplog'

    page_title = '管理日志'
    table_fields = ['op_type', 'status', 'content', 'create_by', 'create_time']
    operations = [{'operation': 'bat-remove', 'label': '批量删除'}]
    img_operations = []
    actions = [
        {'action': 'btn-view', 'label': '查看', 'url': '/sys/oplog/@id'},
        {'action': 'btn-remove', 'label': '删除'},
    ]

    @classmethod
    def format_value(cls, value, key=None, doc=None):
        if key == 'op_type':
            return cls.get_type_name(value)
        if key == 'status':
            return cls.get_status_name(value)
        if key == 'content':
            value, size = str(value), 80
            return '%s%s' % (value[:size], '...' if len(value) > size else '')
        return h.format_value(value, key, doc)

    def get(self):
        """ 运维日志"""
        try:
            kwargs = self.get_template_kwargs()
            condition = dict()
            for field in ['op_type', 'status']:
                value = h.get_url_param(field, self.request.uri)
                value and condition.update({field: value})
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-_id')
            self.render('com/_list.html', docs=docs, pager=pager, q=q, order=order,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class SysOplogHandler(BaseHandler, Oplog):
    URL = ['/sys/oplog/@oid',
           '/sys/oplog/latest',
           '/sys/oplog/latest/@op_type']

    def get(self, id_or_type=None):
        """ 查看运维日志"""
        try:
            if 'latest' in self.request.path:
                condition = {'op_type': id_or_type} if id_or_type else {}
                log = list(self.db.oplog.find(condition).sort('_id', -1).limit(1))
                log = log and log[0]
            else:
                log = self.db.oplog.find_one({'_id': ObjectId(id_or_type)})
            if not log:
                self.send_error_response(e.no_object, message='日志不存在')
            self.render('sys_oplog.html', log=log)

        except Exception as error:
            return self.send_db_error(error)


class ApiTableHandler(BaseHandler):
    URL = '/api'

    def get(self):
        """ 显示后端API和前端路由"""

        def get_doc():
            assert func.__doc__, str(func) + ' no comment'
            return func.__doc__.strip().split('\n')[0]

        handlers = []
        for cls in self.application.handlers:
            handler = cls(self.application, self.request)
            file = 'controller' + re.sub(r'^.+controller', '', inspect.getsourcefile(cls))
            file += '\n' + inspect.getsource(cls).split('\n')[0][:-1]
            for method in handler._get_methods().split(','):
                method = method.strip()
                if method != 'OPTIONS':
                    assert method.lower() in cls.__dict__, cls.__name__
                    func = cls.__dict__[method.lower()]
                    func_name = re.sub(r'<|function |at .+$', '', str(func)).strip()
                    self.add_handlers(cls, file, func_name, get_doc, handlers, method)
        handlers.sort(key=itemgetter(0))
        self.render('_api.html', version=self.application.version, handlers=handlers)

    @staticmethod
    def add_handlers(cls, file, func_name, get_doc, handlers, method):
        def show_roles(roles):
            if 'MyTaskHandler.' in func_name:
                return '普通用户'
            return ','.join(r for r in roles if not re.search(r'员|专家', r) or '普通用户' not in roles)

        def add_handler(url, idx=0):
            roles = get_route_roles(url, method)
            handlers.append((url, func_name, idx, file, get_doc(), show_roles(roles)))

        if isinstance(cls.URL, list):
            for i, url_ in enumerate(cls.URL):
                add_handler(url_, i + 1)
        else:
            add_handler(cls.URL)


class ApiSourceHandler(BaseHandler):
    URL = '/api/code/(.+)'

    def get(self, name):
        """ 显示后端API的源码 """
        for cls in self.application.handlers:
            handler = cls(self.application, self.request)
            for method in handler._get_methods().split(','):
                method = method.strip()
                if method != 'OPTIONS':
                    func = cls.__dict__[method.lower()]
                    func_name = re.sub(r'<|function |at .+$', '', str(func)).strip()
                    if func_name == name:
                        file = 'controller' + re.sub(r'^.+controller', '', inspect.getsourcefile(cls))
                        src = inspect.getsource(cls).strip()
                        return self.render('_api_src.html', name=name, file=file, src=src)
        self.render('_error.html', code=404, message=name + '不存在')
