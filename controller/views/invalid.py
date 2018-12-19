#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from controller.public.base import BaseHandler
from os import path
from operator import itemgetter


class InvalidPageHandler(BaseHandler):
    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return self.render(self.request.path.replace('/', ''))
        self.render('_404.html')


class ApiTable(BaseHandler):
    """ 显示网站所有API和路由的响应类 """

    def get(self):
        handlers = []
        for cls in self.application.handlers:
            p = cls(self.application, self.request)
            for method in p._get_methods().split(','):
                method = method.strip()
                if 'OPTIONS' not in method:
                    func = cls.__dict__[method.lower()]
                    if isinstance(cls.URL, list):
                        for i, s in enumerate(cls.URL):
                            handlers.append((s, method, func.__doc__))
                    else:
                        handlers.append((cls.URL, method, func.__doc__))
        handlers.sort(key=itemgetter(0))
        self.render('_api.html', version=self.application.version, handlers=handlers)
        self.application.load_config()  # reload configure
