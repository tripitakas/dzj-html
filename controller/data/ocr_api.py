#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR接口
@time: 2019/9/2
"""
from controller.base import BaseHandler
from controller import errors
from os import path, remove, system
import json
import logging
import socket
from datetime import datetime

OCR_PATH = path.exists('/srv/deeptext.v3/Web_v2') and '/srv/deeptext.v3/Web_v2'
INPUT_IMAGE_FILE = 'cache/images/image_001.jpg'
OUT_CHAR_TXT_FILE = 'cache/recognition_label/task2_image_001.txt'
OUT_LINE_REC_FILE = 'cache/recognition_label/task3_image_001.txt'
OUT_HYBRID_REC_FILE = 'cache/recognition_label/task4_image_001.txt'
CHAR_TXT_FILE = 'cache/detect_label/task1_image_001.txt'
LOCAL_IMAGE = '_ocr.jpg'
cache = {'count': 0}


def remove_file(filename):
    if path.exists(filename):
        remove(filename)


remove_file(LOCAL_IMAGE)  # 重置任务


class RecognitionApi(BaseHandler):
    URL = '/api/data/ocr'

    def post(self):
        """藏经OCR接口"""
        data = self.get_request_data() or self.request.arguments
        img = self.request.files.get('img')
        assert img
        filename = path.basename(img[0]['filename'])
        data['hybrid'] = 1

        # 设置OCR请求数据
        req = {'multiple_layouts': data.get('multiple_layouts') in [True, 1, 'true', '1'],
               'v_num': int(data.get('v_num', 2)),
               'h_num': int(data.get('h_num', 3))}
        if req['v_num'] < 1 or req['h_num'] < 1:
            return self.send_error_response(errors.ocr_invalid_hv_num)

        # 接收图片文件
        logging.info('%s (%.1f KB) received' % (filename, len(img[0]['body'])))
        if path.exists(LOCAL_IMAGE):
            return self.send_error_response(errors.ocr_busy)
        with open(LOCAL_IMAGE, 'wb') as f:
            f.write(img[0]['body'])
        system('rm -f {0}; ln -fs {1} {0}'.format(self.build_target_filename(INPUT_IMAGE_FILE), LOCAL_IMAGE))

        # 列识别
        result = self.detect_server(req, 8007 if data.get('hybrid') else 8006)
        if result:
            rec_file = self.build_target_filename(OUT_HYBRID_REC_FILE if data.get('hybrid') else OUT_LINE_REC_FILE)
            if path.exists(rec_file):
                rows = open(rec_file).readlines()
                result['rows'] = [r.strip() for r in rows]
            with open('_ocr.json', 'w') as f:
                f.write(json.dumps(result, ensure_ascii=False))
            self.send_data_response(result)

        remove_file(LOCAL_IMAGE)

    def detect_server(self, req, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        start_time = datetime.now()
        try:
            s.connect(('127.0.0.1', port))
        except Exception:
            return self.send_error_response(errors.ocr_off, message=errors.ocr_off[1] % port)
        try:
            s.settimeout(120)
            s.send(json.dumps(req).encode())
            result = s.recv(4096)
            logging.warning('recv ok')
            result = json.loads(result.decode())
            result['run_ms'] = round((datetime.now() - start_time).microseconds / 1000)
            return result
        except Exception as e:
            logging.error(str(e))
            return self.send_error_response(errors.ocr_fail, message=errors.ocr_fail[1] % port)
        finally:
            s.close()

    def build_target_filename(self, cache_filename):
        if OCR_PATH:
            return path.join(OCR_PATH, cache_filename)
        return path.join(self.application.BASE_DIR, 'log', path.basename(cache_filename))
