#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from operator import itemgetter
from os import path
from controller.base import BaseHandler


class InvalidPageHandler(BaseHandler):
    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return self.render(self.request.path.replace('/', ''))
        self.set_status(404, reason='Not found')
        self.render('_404.html')


class ApiTable(BaseHandler):
    URL = '/api'

    def get(self):
        """ 显示网站所有API和路由的响应类 """
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
                            handlers.append((url, method, func.__doc__, auth))
                    elif isinstance(cls.URL, tuple):
                        handlers.append((cls.URL[0], method, func.__doc__, auth))
                    else:
                        handlers.append((cls.URL, method, func.__doc__, auth))
        handlers.sort(key=itemgetter(0))
        self.render('_api.html', version=self.application.version, handlers=handlers)
