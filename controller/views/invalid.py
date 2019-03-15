#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from operator import itemgetter
from os import path
from controller.base.task import TaskHandler
from controller.role import get_route_roles
from model.user import authority_map


class InvalidPageHandler(TaskHandler):
    def prepare(self):
        pass  # ignore roles

    def get(self):
        if self.request.path == '/':
            return self.redirect('/home')
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return self.render(self.request.path.replace('/', ''))
        self.set_status(404, reason='Not found')
        self.render('_404.html')


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
            for method in handler._get_methods().split(','):
                method = method.strip()
                if method != 'OPTIONS':
                    func = cls.__dict__[method.lower()]
                    roles = [authority_map[r] for r in get_route_roles(cls.URL, method)]
                    handlers.append((cls.URL, method, get_doc(), ','.join(roles)))
        handlers.sort(key=itemgetter(0))
        self.render('_api.html', version=self.application.version, handlers=handlers)
