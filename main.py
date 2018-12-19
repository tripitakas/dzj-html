#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 网站服务的主文件
@author: Zhang Yungui
@time: 2018/10/23
"""

import logging
from functools import partial
from tornado import ioloop, netutil, process
from tornado.httpserver import HTTPServer
from tornado.options import define, options as opt
import socket
import os
from controller import app, periodic

define('port', default=8000, help='run port', type=int)
define('num_processes', default=4, help='sub-processes count', type=int)

if __name__ == '__main__':
    opt.parse_command_line()
    opt.debug = opt.debug and opt.port not in [80, 443]
    try:
        app.APP = app.Application()
        ssl_options = not opt.debug and app.APP.site.get('https') or None

        server = HTTPServer(app.APP, xheaders=True, ssl_options=ssl_options)
        sockets = netutil.bind_sockets(opt.port, family=socket.AF_INET)
        fork_id = 0 if opt.debug or os.name == 'nt' else process.fork_processes(opt.num_processes)
        server.add_sockets(sockets)

        app.APP.init_db()
        logging.info('Start the service #%d v%s on %s://localhost:%d' % (
            fork_id, app.__version__, 'https' if ssl_options else 'http', opt.port))
        if fork_id == 0:
            ioloop.PeriodicCallback(partial(periodic.periodic_task, app.APP), 1000 * 300).start()
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        app.APP.stop()
        logging.info('Stop the service')
