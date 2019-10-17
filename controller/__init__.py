#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.com import invalid
from controller import com, cut, data, ocr, punc, search, task, text, user

views = com.views + cut.views + data.views + ocr.views + punc.views + search.views
views += task.views + text.views + user.views

handlers = com.handlers + cut.handlers + data.handlers + ocr.handlers + punc.handlers
handlers += search.handlers + task.handlers + text.handlers + user.handlers

handlers += [invalid.ApiTable, invalid.ApiSourceHandler]

modules = dict(com.modules.items() | text.modules.items())

InvalidPageHandler = invalid.InvalidPageHandler
