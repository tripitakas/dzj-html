#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 在 controller.api 包实现后台的 AJAX 接口

from controller.api import user

handlers = [user.LoginApi, user.RegisterApi, user.LogoutApi, user.ChangeUserApi, user.GetUsersApi,
            user.ResetPasswordApi, user.ChangePasswordApi, user.GetOptionsApi]
