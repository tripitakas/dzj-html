#!/usr/bin/env python
# -*- coding: utf-8 -*-

from . import view, api

views = [
    view.SysScriptHandler, view.SysLogListHandler, view.SysLogHandler,
    view.SysOplogListHandler, view.SysOplogHandler, view.SysUploadOssHandler,
    view.ApiTableHandler, view.ApiSourceHandler,
]

handlers = [
    api.LogDeleteApi, api.OpLogStatusApi, api.SysUploadOssApi,
    api.ResetExamUserApi,
]
