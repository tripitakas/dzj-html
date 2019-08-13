#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import com, task, data, user, tripitaka
from controller.com import invalid

views = com.views + task.views + data.views + user.views + tripitaka.views
handlers = com.handlers + task.handlers + data.handlers + user.handlers + tripitaka.handlers + [
    invalid.ApiTable, invalid.ApiSourceHandler]
modules = dict(com.modules.items() | task.modules.items())
InvalidPageHandler = invalid.InvalidPageHandler
