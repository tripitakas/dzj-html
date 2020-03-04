#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import view, api

views = [
    view.ApiTableHandler, view.ApiSourceHandler, view.AdminScriptHandler,
    view.AdminOplogHandler, view.AdminOplogViewHandler,
]

handlers = [
    api.DeleteOplogApi,
]
