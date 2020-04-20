#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 网站服务的主文件
@time: 2018/10/23
"""

import os
import sys
import socket
import logging

sys.path.append('/extra_modules')

from tornado.httpserver import HTTPServer
from tornado import ioloop, netutil, process
from tornado.options import define, options as opt

import controller as c
from controller.app import Application

define('num_processes', default=4, help='sub-processes count', type=int)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    opt.parse_command_line()
    routes = c.handlers + c.views
    app = Application(routes, default_handler_class=c.InvalidPageHandler, ui_modules=c.modules, xsrf_cookies=True)
    try:
        ssl_options = not opt.debug and app.site.get('https') or None
        server = HTTPServer(app, xheaders=True, ssl_options=ssl_options)
        sockets = netutil.bind_sockets(opt.port, family=socket.AF_INET)
        fork_id = 0 if 1 or opt.debug or os.name == 'nt' else process.fork_processes(opt.num_processes)
        server.add_sockets(sockets)
        protocol = 'https' if ssl_options else 'http'
        logging.info('Start the service #%d v%s on %s://localhost:%d' % (fork_id, app.version, protocol, opt.port))
        if fork_id == 0 and app.config.get('auto_script'):
            script = app.db and 'sh start_worker.sh {0} {1}'.format(app.db_uri, app.config['database']['name'])
            os.system(script)
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        app.stop()
        logging.info('Stop the service')
