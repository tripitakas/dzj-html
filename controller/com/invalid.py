#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

import re
import inspect
from os import path
from operator import itemgetter
from tornado.web import RequestHandler
from controller.task.base import TaskHandler
from controller.auth import get_route_roles


class InvalidPageHandler(TaskHandler):
    def prepare(self):
        pass  # ignore roles

    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return RequestHandler.render(self, self.request.path.replace('/', ''))
        self.set_status(404, reason='Not found')
        self.render('_404.html')

    def post(self):
        self.get()


class ApiTable(TaskHandler):
    URL = '/api'

    def get(self):
        """ 显示后端API和前端路由 """

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
            added = 0
            if '@box_type' in url:
                for s, box_type in enumerate(['block', 'char', 'column', 'text']):
                    sub_url = url.replace('@box_type', box_type)
                    roles = get_route_roles(sub_url, method)
                    if roles:
                        added += len(roles)
                        handlers.append((sub_url, func_name, idx * 10 + s + 1, file, get_doc(), show_roles(roles)))
            if not added:
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
