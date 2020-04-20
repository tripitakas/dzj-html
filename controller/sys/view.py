#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/12/08
"""
import re
import inspect
from .oplog import Oplog
from operator import itemgetter
from bson.objectid import ObjectId
from controller import errors as e
from controller.base import BaseHandler
from controller.auth import get_route_roles
from controller.task.base import TaskHandler


class SysScriptHandler(BaseHandler):
    URL = '/sys/script'

    def get(self):
        """ 系统脚本管理"""
        tripitakas = ['所有'] + self.db.tripitaka.find().distinct('tripitaka_code')
        self.render('sys_script.html', tripitakas=tripitakas)


class SysOplogListHandler(BaseHandler, Oplog):
    URL = '/sys/oplog'

    def get(self):
        """ 管理日志"""
        condition = {}
        docs, pager, q, order = self.find_by_page(self, condition, default_order='-_id')
        kwargs = self.get_template_kwargs()
        self.render('sys_oplog_list.html', docs=docs, pager=pager, q=q, order=order,
                    format_value=self.format_value, **kwargs)


class SysOplogHandler(BaseHandler, Oplog):
    URL = ['/sys/oplog/@oid', '/sys/oplog/(latest)']

    def get(self, oid):
        """ 管理日志"""
        if oid == 'latest':
            log = list(self.db.oplog.find().sort('_id', -1).limit(1))
            log = log and log[0]
        else:
            log = self.db.oplog.find_one({'_id': ObjectId(oid)})
        if not log:
            self.send_error_response(e.no_object, message='日志不存在')
        self.render('sys_oplog.html', log=log)


class ApiTableHandler(TaskHandler):
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


class ApiSourceHandler(TaskHandler):
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
