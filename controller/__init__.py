#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.com import invalid
from controller import com, data, task, char, page, user, article, sys

views = com.views + data.views + task.views + char.views
views += page.views + user.views + article.views + sys.views

handlers = com.handlers + data.handlers + task.handlers + char.handlers
handlers += page.handlers + user.handlers + article.handlers + sys.handlers

modules = com.modules

InvalidPageHandler = invalid.InvalidPageHandler
