#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, data, task, page, user, article, admin
from controller.com import invalid

views = com.views + data.views + task.views
views += page.views + user.views + article.views + admin.views

handlers = com.handlers + data.handlers + task.handlers
handlers += page.handlers + user.handlers + article.handlers + admin.handlers

modules = dict(list(com.modules.items()) + list(page.modules.items()))

InvalidPageHandler = invalid.InvalidPageHandler
