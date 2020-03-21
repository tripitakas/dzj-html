#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller.data.data import Char
from controller.task.base import TaskHandler


class CharHandler(TaskHandler, Char):

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)

    def prepare(self):
        super().prepare()

    def page_title(self):
        return self.task_name()
