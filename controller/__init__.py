#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, task, data, user, tripitaka, cut, text
from controller.com import invalid

views = com.views + task.views + data.views + user.views + tripitaka.views + cut.views + text.views
handlers = com.handlers + task.handlers + data.handlers + user.handlers + tripitaka.handlers
handlers += cut.handlers + text.handlers + [invalid.ApiTable, invalid.ApiSourceHandler]
modules = dict(com.modules.items() | text.modules.items())
InvalidPageHandler = invalid.InvalidPageHandler
