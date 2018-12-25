#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 在 controller.api 包实现后台的 AJAX 接口
# 在 controller.views 包实现页面响应类，生成前端页面，modules 为重用网页片段的渲染类

from controller import api, views
from controller.views import invalid

handlers = api.handlers + views.handlers + [invalid.ApiTable]
modules = views.modules
InvalidPageHandler = invalid.InvalidPageHandler
