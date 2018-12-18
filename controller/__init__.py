#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller import home, user as r

handlers = [home.HomeHandler, user.LoginHandler, user.RegisterHandler, user.UsersHandler]
InvalidPageHandler = home.InvalidPageHandler
