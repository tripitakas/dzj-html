#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 网站应用类
@time: 2018/10/23
"""

import re
from os import path
from tornado import web
from operator import itemgetter
from tornado.log import access_log
from tornado.options import define, options
from controller.auth import url_placeholder
from controller.helper import BASE_DIR, load_config, connect_db

__version__ = '0.1.113.21228'

define('port', default=8000, help='run port', type=int)
define('debug', default=True, help='the debug mode', type=bool)
define('testing', default=False, help='the testing mode', type=bool)


class Application(web.Application):
    def __init__(self, handlers, **settings):
        self._db = self._db_test = self.db_uri = self.config = self.site = None
        self.init_config(settings.get('db_name_ext'))

        self.IMAGE_PATH = path.join(BASE_DIR, 'static', 'img')
        self.version = __version__ + '-work'
        self.BASE_DIR = BASE_DIR
        self.handlers = handlers
        handlers = [(r'/upload/(\w+/\w+\.(png|jpg|jpeg|gif|bmp))', web.StaticFileHandler,
                     dict(path=path.join(BASE_DIR, 'static', 'upload')))]

        for cls in self.handlers:
            if isinstance(cls.URL, list):
                handlers.extend((self.url_replace(url), cls) for url in cls.URL)
            else:
                handlers.append((self.url_replace(cls.URL), cls))

        handlers = sorted(handlers, key=itemgetter(0))
        web.Application.__init__(
            self, handlers,
            debug=options.debug,
            login_url='/user/login',
            static_path=path.join(BASE_DIR, 'static'),
            template_path=path.join(BASE_DIR, 'views'),
            cookie_secret=self.config['cookie_secret'],
            log_function=self.log_function,
            **settings
        )

    @staticmethod
    def url_replace(url):
        for k, v in url_placeholder.items():
            url = url.replace('@' + k, '(%s)' % v)
        return url

    @staticmethod
    def log_function(handler):
        summary = handler._request_summary()
        s = handler.get_status()
        if not (s in [304, 200] and re.search(r'GET /(static|api/(pull|message|discuss))', summary) or s == 404):
            user = hasattr(handler, 'current_user') and handler.current_user
            username = user and (hasattr(user, 'name') and user.name or user.get('name')) or ''
            request_time = 1000.0 * handler.request.request_time()
            cls = re.split("[.']", str(handler.__class__))[-2]
            log_method = access_log.info if s < 400 else access_log.warning if s < 500 else access_log.error
            log_method("%d %s %s %.2fms%s", s, summary, cls, request_time, username and ' [%s]' % username or '')

    @property
    def db(self):
        if not self._db:
            self._db, self.db_uri = connect_db(self.config['database'])
        return self._db

    @property
    def db_test(self):
        if not self._db_test:
            self._db_test, uri = connect_db(self.config['database'], '_test')
        return self._db_test

    def init_config(self, db_name_ext=None):
        self.config = load_config()
        self.site = self.config['site']
        self.site['url'] = 'localhost:{0}'.format(options.port)
        if db_name_ext and not self.config['database']['name'].endswith('_test'):
            self.config['database']['name'] += db_name_ext

    def stop(self):
        pass
