#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 在 controller.com 包实现页面响应类，生成前端页面，modules 为重用网页片段的渲染类

from . import module, view, api

views = [
    view.HomeHandler,
]

handlers = [
    api.SessionConfigApi
]

modules = {
    'ComLeft': module.ComLeft, 'ComHead': module.ComHead, 'Pager': module.Pager, 'ComTable': module.ComTable,
    'ComModal': module.ComModal, 'ReturnModal': module.ReturnModal, 'DoubtModal': module.DoubtModal,
    'TaskRemarkModal': module.TaskRemarkModal, 'AutoPickModal': module.AutoPickModal,
    'PageRemarkModal': module.PageRemarkModal,
}
