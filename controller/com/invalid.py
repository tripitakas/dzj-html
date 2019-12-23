#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/23
"""

import logging
from os import path
from tornado.web import RequestHandler
from controller.task.base import TaskHandler


class InvalidPageHandler(TaskHandler):
    def prepare(self):
        pass  # ignore roles

    def get(self):
        if '/api/' in self.request.path:
            self.set_status(404, reason='Not found')
            return self.finish()
        if path.exists(path.join(self.get_template_path(), self.request.path.replace('/', ''))):
            return RequestHandler.render(self, self.request.path.replace('/', ''))
        logging.error('%s not found' % self.request.path)
        self.set_status(404, reason='Not found')
        self.render('_404.html')

    def post(self):
        self.get()
