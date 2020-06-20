#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 将本地static/img中的chars、columns中的图片上传到OSS上
# python3 utils/extract_img.py --condition= --user_name=

import os
import sys
import logging
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from utils.oss import Oss
from controller import helper as hp
from controller import errors as err


def upload_oss(img_type='', only_check=False):
    """ 将本地static/img中的chars、columns中的图片上传到OSS上"""
    # 检查参数
    cfg = hp.load_config()
    my_cloud = hp.prop(cfg, 'web_img.my_cloud')
    key_id, key_secret = hp.prop(cfg, 'web_img.key_id'), hp.prop(cfg, 'web_img.key_secret')
    if not my_cloud or not key_id or not key_secret:
        return err.no_my_cloud

    oss_web = Oss(my_cloud, key_id, key_secret, hp.prop(cfg, 'web_img.use_internal'))
    if not oss_web.is_writeable():
        if not oss_web.is_readable():
            return err.oss_not_readable
        else:
            return err.oss_not_writeable[0], 'OSS可读，不可写'

    if only_check:
        return True

    # 批量上传
    assert img_type in ['char', 'column']
    logging.info('[%s]upload_oss.py script started, img_type %s.' % (hp.get_date_time(), img_type))
    try:
        img_root = path.join(BASE_DIR, 'static', 'img', img_type + 's')
        for root, dirs, files in os.walk(img_root):
            for fn in files:
                if not fn.endswith('.jpg'):
                    continue
                file = path.join(root, fn)
                inner_path = '/'.join([s for s in fn.split('_') if len(s) < 10][:-1])
                oss_file = path.join(img_type + 's', inner_path, fn)
                r = oss_web.upload_file(oss_file, file)
                if r.status == 200:
                    os.remove(file)
                logging.info(
                    '[%s]%s, upload %s.' % (hp.get_date_time(), fn, 'success' if r.status == 200 else 'failed'))
    except Exception as e:
        logging.info('[%s] %s' % (e.__class__.__name__, str(e)))


if __name__ == '__main__':
    import fire

    fire.Fire(upload_oss)
