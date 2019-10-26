#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import os.path as path
import tests.users as u
import controller.errors as e
from tests.testcase import APITestCase
from utils.build_meta import *


class TestBuildMeta(APITestCase):
    def setUp(self):
        super(TestBuildMeta, self).setUp()

    def test_build_meta(self):
        # 测试获取跟目录
        import_dir = '/srv/nextcloud/data/zhangsan/files/XX-某藏/1-正法明目'
        base = get_import_base(import_dir)
        self.assertEqual(base, '/srv/nextcloud/data/zhangsan/files/')

        # 测试获取藏经代码或组织机构
        tripitaka_code = get_tripitaka_code(base, import_dir)
        self.assertEqual(tripitaka_code, 'XX')

        # 设置参数
        work_dir = path.join(path.dirname(__file__), '..', '..', 'meta', 'import_sample', 'work_dir')
        import_base = path.join(path.dirname(__file__), '..', '..', 'meta', 'import_sample', 'user_dir')

        # 测试命名格式不规范
        import_dir = path.join(import_base, 'YY', '1-正法明目', '1A-名称不规范')
        r = build(import_dir, import_base, work_dir)
        self.assertFalse(r)

        # 测试获取存储层次不一致
        import_dir = path.join(import_base, 'YY', '2-层次不一致')
        r = build(import_dir, import_base, work_dir)
        self.assertFalse(r)

        # 测试生成册信息
        import_dir = path.join(import_base, 'XX')
        r = build(import_dir, import_base, work_dir)
        self.assertTrue(r is not False)
