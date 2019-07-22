#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 在 controller.com 包实现页面响应类，生成前端页面，modules 为重用网页片段的渲染类

from . import modules, home

views = [
    home.HomeHandler,
]
handlers = [
]
modules = {
    'CommonLeft': modules.CommonLeft, 'CommonHead': modules.CommonHead, 'Pager': modules.Pager
}
