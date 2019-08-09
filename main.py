#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 网站服务的主文件
@time: 2018/10/23
"""

import logging
import os
import socket
from functools import partial
import sys
sys.path.append('/extra_modules')

from tornado import ioloop, netutil, process
from tornado.httpserver import HTTPServer
from tornado.options import define, options as opt

import controller as c
from controller.app import Application
from controller.periodic import periodic_task

define('num_processes', default=4, help='sub-processes count', type=int)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    opt.parse_command_line()
    opt.debug = opt.debug and opt.port not in [80, 443]
    routes = c.handlers + c.views
    app = Application(routes, default_handler_class=c.InvalidPageHandler, ui_modules=c.modules, xsrf_cookies=True)
    try:
        ssl_options = not opt.debug and app.site.get('https') or None
        server = HTTPServer(app, xheaders=True, ssl_options=ssl_options)
        sockets = netutil.bind_sockets(opt.port, family=socket.AF_INET)
        fork_id = 0 if opt.debug or os.name == 'nt' else process.fork_processes(opt.num_processes)
        server.add_sockets(sockets)
        protocol = 'https' if ssl_options else 'http'
        logging.info('Start the service #%d v%s on %s://localhost:%d' % (fork_id, app.version, protocol, opt.port))
        if fork_id == 0:
            ioloop.PeriodicCallback(partial(periodic_task, app), 1000 * 300).start()
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        app.stop()
        logging.info('Stop the service')
