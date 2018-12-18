#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/10/23
"""

from tornado.web import RequestHandler
from operator import itemgetter


class ApiTable(RequestHandler):
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
