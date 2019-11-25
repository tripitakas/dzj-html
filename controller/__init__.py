#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.com import invalid
from controller import com, cut, data, task, text, tool, user, article

views = com.views + cut.views + data.views + tool.views + article.views
views += task.views + text.views + user.views

handlers = com.handlers + cut.handlers + data.handlers + tool.handlers
handlers += task.handlers + text.handlers + user.handlers + article.handlers
handlers += [invalid.ApiTable, invalid.ApiSourceHandler]

modules = dict(com.modules.items() | text.modules.items())

InvalidPageHandler = invalid.InvalidPageHandler
