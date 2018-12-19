#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 网站应用类
@author: Zhang Yungui
@time: 2018/10/23
"""

from os import path
from tornado import web
from tornado.options import define, options
import pymongo
import yaml
import pymysql
from operator import itemgetter
import re
from tornado.log import access_log

from controller import api, views
from controller.views import invalid


__version__ = '0.0.1.81218'
APP = None
BASE_DIR = path.dirname(path.dirname(__file__))
define('debug', default=True, help='the debug mode', type=bool)


class Application(web.Application):
    def __init__(self, **settings):
        self.db = self.config = self.site = None
        self.load_config()

        self.version = __version__
        self.BASE_DIR = BASE_DIR
        self.handlers = api.handlers + views.handlers
        handlers = [('/api', invalid.ApiTable)]

        for cls in self.handlers:
            if isinstance(cls.URL, list):
                handlers.extend((s, cls) for s in cls.URL)
            else:
                handlers.append((cls.URL, cls))
        handlers = sorted(handlers, key=itemgetter(0))
        web.Application.__init__(self, handlers, debug=options.debug,
                                 login_url='/login',
                                 compiled_template_cache=False,
                                 static_path=path.join(BASE_DIR, 'static'),
                                 template_path=path.join(BASE_DIR, 'views'),
                                 cookie_secret=self.config['cookie_secret'],
                                 xsrf_cookies=True,
                                 default_handler_class=invalid.InvalidPageHandler,
                                 log_function=self.log_function,
                                 **settings)

    @staticmethod
    def log_function(handler):
        if handler.get_status() < 400:
            log_method = access_log.info
        elif handler.get_status() < 500:
            log_method = access_log.warning
        else:
            log_method = access_log.error
        summary = handler._request_summary()
        if not(handler.get_status() in [304, 200] and re.search(r'GET /(static|api/(pull|message|discuss))', summary)):
            nickname = hasattr(handler, 'current_user') and handler.current_user
            nickname = nickname and (hasattr(nickname, 'name') and nickname.name or nickname.get('name')) or ''
            request_time = 1000.0 * handler.request.request_time()
            log_method("%d %s %.2fms%s", handler.get_status(),
                       summary, request_time, nickname and ' [%s]' % nickname or '')

    def init_db(self):
        conn = pymongo.MongoClient('localhost', connectTimeoutMS=2000, serverSelectionTimeoutMS=2000,
                                   maxPoolSize=10, waitQueueTimeoutMS=5000)
        self.db = conn.tripitaka

    def load_config(self):
        param = dict(encoding='utf-8')
        with open(path.join(BASE_DIR, 'app.yml'), **param) as f:
            self.config = yaml.load(f)
            self.site = self.config['site']
            self.site['url'] = 'localhost:{0}'.format(options.port)

    def open_connection(self):
        cfg = dict(self.config['database'])
        return pymysql.connect(host=cfg['host'],
                               port=cfg['port'],
                               user=cfg['dbuser'],
                               passwd=cfg['password'],
                               db=cfg['dbname'],
                               connect_timeout=3,
                               read_timeout=3,
                               write_timeout=5,
                               charset='utf8mb4')

    def stop(self):
        pass
