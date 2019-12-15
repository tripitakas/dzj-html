#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, cut, data, task, text, tool, user, article, admin
from controller.com import invalid

views = com.views + cut.views + data.views + tool.views + task.views
views += text.views + user.views + article.views + admin.views

handlers = com.handlers + cut.handlers + data.handlers + tool.handlers + task.handlers
handlers += text.handlers + user.handlers + article.handlers + admin.handlers

modules = dict(list(com.items()) + list(text.items()))

InvalidPageHandler = invalid.InvalidPageHandler
