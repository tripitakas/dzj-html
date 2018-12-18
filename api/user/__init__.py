#!/usr/bin/env python
# -*- coding: utf-8 -*-

from api.user import user

handlers = [user.LoginHandler, user.RegisterHandler, user.LogoutHandler,
            user.ChangeUserHandler, user.GetUsersHandler,
            user.ResetPasswordHandler, user.ChangePasswordHandler, user.GetOptionsHandler]
