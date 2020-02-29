#!/usr/bin/env python
# -*- coding: utf-8 -*-

import oss2


class Cut(object):

    def __init__(self, **kwargs):
        pass

    @staticmethod
    def can_read(bucket):
        try:
            bucket.list_objects('')
            return True
        except oss2.exceptions:
            return False

    @staticmethod
    def can_write(bucket):
        try:
            bucket.put_object('1.tmp', '')
            bucket.delete_object('1.tmp')
            return True
        except oss2.exceptions:
            return False

    @staticmethod
    def file_exist():
        pass