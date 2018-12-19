#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.views import home, user

handlers = [home.HomeHandler, user.LoginHandler, user.RegisterHandler, user.UsersHandler]
