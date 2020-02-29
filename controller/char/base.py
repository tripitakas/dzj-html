#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .char import Char
from controller.task.base import TaskHandler


class CharHandler(TaskHandler, Char):

    def __init__(self, application, request, **kwargs):
        super(CharHandler, self).__init__(application, request, **kwargs)

    def get_char_img(self, char=None, char_id=None):
        char_id = char_id if char_id else char.get('id')
        return self.get_web_img(char_id, img_type='char')
