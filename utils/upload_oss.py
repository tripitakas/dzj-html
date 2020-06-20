#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 将本地static/img中的chars、columns中的图片上传到OSS上
# python3 utils/extract_img.py --condition= --user_name=

import os
import sys
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from utils.oss import Oss
from controller import helper as hp
from controller import errors as err


def upload_oss(img_type=''):
    """ 将本地static/img中的chars、columns中的图片上传到OSS上"""
    assert img_type in ['chars', 'columns']
    # 检查参数
    cfg = hp.load_config()
    my_cloud = hp.prop(cfg, 'web_img.my_cloud')
    key_id, key_secret = hp.prop(cfg, 'web_img.key_id'), hp.prop(cfg, 'web_img.key_secret')
    if not my_cloud or not key_id or not key_secret:
        return err.no_my_cloud

    oss_web = Oss(my_cloud, key_id, key_secret, hp.prop(cfg, 'web_img.use_internal'))
    if not oss_web.is_writeable():
        return err.oss_not_readable if not oss_web.is_readable() else (err.oss_not_writeable[0], 'OSS可读，不可写')

    # 批量上传
    print('[%s]upload_oss.py script started.' % hp.get_date_time())
    try:
        img_root = path.join(BASE_DIR, 'static', 'img', 'chars/GL/8/5/10')
        for root, dirs, files in os.walk(img_root):
            for fn in files:
                file = path.join(root, fn)
                inner_path = '/'.join([s for s in fn.split('_') if len(s) < 10][:-1])
                r = oss_web.upload_file(path.join(img_type, inner_path, fn), file)
                if r.status == 200:
                    os.remove(file)
                print('[%s]%s, upload %s.' % (hp.get_date_time(), fn, 'success' if r.status == 200 else 'failed'))
    except Exception as e:
        print('[%s] %s' % (e.__class__.__name__, str(e)))


if __name__ == '__main__':
    import fire

    fire.Fire(upload_oss)
