#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import oss2
import json
import math
import hashlib
from os import path
from PIL import Image

BASE_DIR = path.dirname(path.dirname(path.dirname(__file__)))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.base import BaseHandler as Bh


def publish_char_task():
    return True


if __name__ == '__main__':
    import fire

    fire.Fire(publish_char_task)
