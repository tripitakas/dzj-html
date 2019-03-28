#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, task, data, user
from controller.com import invalid

views = com.views + task.views + data.views + user.views
handlers = com.handlers + task.handlers + data.handlers + user.handlers + [invalid.ApiTable, invalid.ApiSourceHandler]
modules = com.modules
InvalidPageHandler = invalid.InvalidPageHandler
