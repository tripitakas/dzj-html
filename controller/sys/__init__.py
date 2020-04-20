#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import view, api

views = [
    view.ApiTableHandler, view.ApiSourceHandler, view.SysScriptHandler,
    view.SysOplogListHandler, view.SysOplogHandler,
]

handlers = [
    api.OplogDeleteApi,
]
