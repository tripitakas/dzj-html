#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR接口
@time: 2019/9/2
"""
import re
import csv
import json
import logging
import hashlib
from glob2 import glob
from os import path, remove
from datetime import datetime
import controller.validate as va
from utils.add_pages import add_page
from urllib.parse import urlencode
from controller.helper import prop
from controller import errors as e
from controller.base import BaseHandler
from controller.tool.ocr import ocr2page
from controller.data.data import Reel, Volume, Sutra

from boto3.session import Session
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError


class SubmitRecognitionApi(BaseHandler):
    URL = '/api/data/submit_ocr/@img_file'

    def post(self, img_name):
        """从OCR结果文件创建页面任务"""
        upload_ocr = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr')
        img_file = path.join(upload_ocr, img_name)
        if not path.exists(img_file):
            return self.send_error_response(e.ocr_img_not_existed)
        json_file = path.join(upload_ocr, img_name.split('.')[0] + '.json')
        if not path.exists(json_file):
            return self.send_error_response(e.ocr_json_not_existed)

        page = self.upload_page(self, json_file, img_file)
        if page:
            self.add_op_log('submit_ocr', target_id=page['id'], context=page['imgname'])
            self.send_data_response(dict(name=page['imgname'], id=page['id']))

    def get(self, result_folder):
        """批量导入OCR结果"""
        result_path = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr', result_folder)
        if not path.exists(result_path) or not path.isdir(result_path):
            return self.send_error_response(e.ocr_img_not_existed)
        files = sorted(glob(path.join(result_path, '**', '*.json')))
        added = []
        existed = 0
        for json_file in files:
            page = self.upload_page(self, json_file, None, ignore_error=True)
            if page == e.ocr_page_existed:
                existed += 1
            elif isinstance(page, dict):
                added.append(page['imgname'])
        self.add_op_log('submit_ocr_batch', context=str(len(added)))
        self.send_data_response(dict(count=len(added), pages=added, existed=existed))

    @staticmethod
    def upload_page(self, json_file, img_file, ignore_error=False, update=False):
        try:
            with open(json_file) as f:
                page = json.load(f)
        except (ValueError, OSError) as err:
            logging.error('%s: %s' % (json_file, str(err)))
            return e.ocr_json_not_existed if ignore_error else self.send_error_response(e.ocr_json_not_existed)
        page = ocr2page(page)

        img_name = path.basename(json_file).split('.')[0]
        if re.match(r'^[A-Z]{2}(_[0-9]+)+$', img_name):
            page['imgname'] = img_name
        if not re.match(r'^[a-zA-Z]{2}(_[0-9]+){2,3}', page['imgname']):
            return e.ocr_invalid_name if ignore_error else self.send_error_response(e.ocr_invalid_name)
        r = add_page(page['imgname'], page, self.db, update=update)
        if not r:
            return e.ocr_page_existed if ignore_error else self.send_error_response(e.ocr_page_existed)

        if 'secret_key' in self.config['img'] and self.config['img'].get('salt') and img_file and path.exists(img_file):
            SubmitRecognitionApi.upload_oss(self, img_file)

        return page

    @staticmethod
    def upload_oss(self, img_file):
        oss = self.config['img']
        session = Session(aws_access_key_id=oss['access_key'], aws_secret_access_key=oss['secret_key'],
                          region_name=oss['region_name'])
        s3 = session.resource('s3', endpoint_url=oss['host'])

        key, volumes, cur_volume = None, set(), ''
        try:
            fn = path.basename(img_file)
            page_code = fn.split('.')[0]
            md5 = hashlib.md5()
            md5.update((page_code + oss['salt']).encode('utf-8'))
            new_name = '%s_%s.jpg' % (page_code, md5.hexdigest())
            key = '/'.join(page_code.split('_')[:-1] + [new_name])
            s3.meta.client.upload_file(img_file, 'pages', key)
            logging.info('%s uploaded' % key)
            return key
        except (Boto3Error, BotoCoreError) as err:
            logging.error('fail to upload %s: %s' % (key, str(err).split(': ')[-1]))


class ImportMetaApi(BaseHandler):
    URL = '/api/data/import_meta'

    def post(self):
        """生成藏册页数据并导入"""

        def handle_response(res):
            self.add_op_log('import_meta', context='%s,%s,%d,%d' % (
                data['user_code'], data['tripitaka_code'], len(res['pages']), len(res['volumes'])))

            err_volumes = save(res, 'volumes', Volume)
            err_sutras = save(res, 'sutras', Sutra)
            err_reels = save(res, 'reels', Reel)

            error = err_volumes or err_sutras or err_reels
            if error:
                return self.send_error_response(e.ocr_import, message=e.ocr_import[1] % error)

            res['new_pages'] = []
            for name in res['pages']:
                assert re.match(r'^[A-Z]{2}(_\d+)+$', name)
                if not self.db.page.find_one(dict(name=name)):
                    page = dict(name=name, kind=name[:2], create_time=datetime.now())
                    self.db.page.insert_one(page)
                    res['new_pages'].append(name)
                    logging.info('page %s added' % name)

            self.call_back_api(url, body='', method='POST', handle_error=lambda t: logging.error(t),
                               handle_response=lambda r: self.send_data_response(res))

        def save(res, name, cls):
            if res[name]:
                with open(name + '.csv', 'w') as f:
                    csv.writer(f).writerows(res[name])
                with open(name + '.csv') as f:
                    r = cls.save_many(self.db, file_stream=f)
                remove(name + '.csv')
                if r.get('status') == 'success':
                    logging.info('import %s success: %s' % (name, r.get('message')))
                else:
                    logging.error('import %s failed: %s' % (name, r.get('message')))
                    return r.get('message')

        data = self.get_request_data()
        rules = [
            (va.not_empty, 'user_code', 'tripitaka_code'),
            (va.is_tripitaka, 'tripitaka_code'),
            (va.is_digit, 'h_num', 'v_num'),
            (va.between, 'h_num', 1, 9),
            (va.between, 'v_num', 1, 9),
        ]
        err = va.validate(data, rules)
        if err:
            return self.send_error_response(err)

        url = '%s?%s' % (prop(self.config, 'ocr.api')[:-3] + 'build_meta', urlencode(data))
        self.call_back_api(
            url, handle_response=handle_response,
            handle_error=lambda t: self.send_error_response(e.ocr_import, message=e.ocr_import[1] % (t or '无法访问'))
        )


class FetchResultApi(BaseHandler):
    URL = '/api/data/fetch_ocr/@user_code'

    def get(self, user_code):
        """拉取OCR结果"""

        def handle_list_response(res):
            def handle_file(body):
                json_file = path.join(self.application.BASE_DIR, 'static', 'upload', 'f%d.json' % abs(hash(body)))
                with open(json_file, 'wb') as f:
                    f.write(body)
                pages.append(json_file)
                loop()

            def loop():
                if res:
                    json_file = res.pop()['path']
                    if not json_file.endswith('.json'):
                        return loop()
                    logging.info('fetch %s' % json_file)
                    self.call_back_api('%s/%s?remove=1' % (prop(self.config, 'ocr.api')[:-3] + 'browse', json_file),
                                       handle_response=handle_file, handle_error=handle_error,
                                       binary_response=True)
                else:
                    for json_file in pages:
                        page = SubmitRecognitionApi.upload_page(self, json_file, None, ignore_error=True, update=True)
                        if page and isinstance(page, dict):
                            self.add_op_log('submit_ocr', target_id=page['id'], context=page['imgname'])
                            result.append(page['imgname'])
                        if path.exists(json_file):
                            remove(json_file)

                    self.send_data_response(dict(pages=result))

            pages, result = [], []
            loop()

        def handle_error(t):
            self.send_error_response(e.ocr_import, message=e.ocr_import[1] % (t or '无法访问'))

        self.call_back_api('%s//work_path/_result/%s' % (prop(self.config, 'ocr.api')[:-3] + 'browse', user_code),
                           handle_response=handle_list_response, handle_error=handle_error)
