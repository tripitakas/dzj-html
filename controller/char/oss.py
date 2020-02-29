#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import oss2
from os import path

class Oss(object):

    def __init__(self, key_id, key_secret, end_point, bucket, **kwargs):
        self.key_id = key_id
        self.key_secret = key_secret
        self.end_point = end_point
        self.auth = oss2.Auth(key_id, key_secret)
        self.bucket = oss2.Bucket(self.auth, end_point, bucket)

    def can_read(self):
        try:
            self.bucket.list_objects('')
            return True
        except oss2.exceptions:
            return False

    def can_write(self):
        try:
            self.bucket.put_object('1.tmp', '')
            self.bucket.delete_object('1.tmp')
            return True
        except oss2.exceptions:
            return False

    def download_file(self, oss_file, save_to):
        self.bucket.get_object_to_file(oss_file, save_to)