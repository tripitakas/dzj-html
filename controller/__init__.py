#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, data, task, char, page, user, article, sys
from controller.com import invalid

views = com.views + data.views + task.views + char.views
views += page.views + user.views + article.views + sys.views

handlers = com.handlers + data.handlers + task.handlers + char.handlers
handlers += page.handlers + user.handlers + article.handlers + sys.handlers

modules = dict(list(com.modules.items()) + list(page.modules.items()))

InvalidPageHandler = invalid.InvalidPageHandler
