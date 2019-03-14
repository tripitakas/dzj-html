#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from operator import itemgetter
from os import path
from controller.base.task import TaskHandler


class InvalidPageHandler(TaskHandler):
    def prepare(self):
        pass  # ignore roles

    def get(self):
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
        """ 显示网站所有API和路由的响应类 """

        def get_doc():
            return func.__doc__.strip().split('\n')[0]

        handlers = []
        for cls in self.application.handlers:
            handler = cls(self.application, self.request)
            auth = (','.join(list(cls.AUTHORITY)) if isinstance(cls.AUTHORITY, tuple) else cls.AUTHORITY)\
                if hasattr(cls, 'AUTHORITY') else ''
            for method in handler._get_methods().split(','):
                method = method.strip()
                if method != 'OPTIONS':
                    func = cls.__dict__[method.lower()]
                    if isinstance(cls.URL, list):
                        for i, url in enumerate(cls.URL):
                            handlers.append((url, method, get_doc(), auth))
                    elif isinstance(cls.URL, tuple):
                        handlers.append((cls.URL[0], method, get_doc(), auth))
                    else:
                        handlers.append((cls.URL, method, get_doc(), auth))
        handlers.sort(key=itemgetter(0))
        self.render('_api.html', version=self.application.version, handlers=handlers)
