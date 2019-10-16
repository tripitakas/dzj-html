#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, task, data, user, data, cut, text
from controller.com import invalid

views = com.views + task.views + data.views + user.views + data.views + cut.views + text.views
handlers = com.handlers + task.handlers + user.handlers + data.handlers
handlers += cut.handlers + text.handlers + [invalid.ApiTable, invalid.ApiSourceHandler]
modules = dict(com.modules.items() | text.modules.items())
InvalidPageHandler = invalid.InvalidPageHandler
