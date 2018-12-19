#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.api import user

handlers = [user.LoginApi, user.RegisterApi, user.LogoutApi,
            user.ChangeUserApi, user.GetUsersApi,
            user.ResetPasswordApi, user.ChangePasswordApi, user.GetOptionsApi]
