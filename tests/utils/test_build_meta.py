#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/05/07
"""
import shutil
from glob2 import glob
from tests.testcase import APITestCase
from utils.build_meta import *


class TestBuildMeta(APITestCase):
    def setUp(self):
        super(TestBuildMeta, self).setUp()

    def test_build_meta(self):
        # 设置参数
        work_dir = path.join(path.dirname(__file__), '..', '..', 'meta', 'import_sample', 'work_dir')
        import_base = path.join(path.dirname(__file__), '..', '..', 'meta', 'import_sample', 'user_dir')

        # 清空上次生成的数据文件
        if path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.mkdir(work_dir)
        for root, dirs, files in os.walk(import_base, topdown=True):
            for filename in files:
                if filename.split('.')[-1] in ['csv', 'json']:
                    os.remove(path.join(root, filename))

        # 测试获取跟目录
        import_dir = '/srv/nextcloud/data/zhangsan/files/XX-某藏/1-正法明目'
        base = get_import_base(import_dir)
        self.assertEqual(base, '/srv/nextcloud/data/zhangsan/files/')

        # 测试获取藏经代码或组织机构
        tripitaka_code = get_tripitaka_code(base, import_dir)
        self.assertEqual(tripitaka_code, 'XX')

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
