#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller.page.tool.rare import format_rare
from controller.page.tool.variant import normalize


class TestSpecialText(APITestCase):

    def test_utf8mb4(self):
        name = 'GL_1056_5_6'
        page = self._app.db.page.find_one({'name': name})
        ocr = page.get('ocr', '') + '卷北鿌沮渠蒙遜' + '\U0002e34f'
        self._app.db.page.update_one({'name': name}, {'$set': {'ocr': ocr}})
        page = self._app.db.page.find_one({'name': name})
        ocr = page.get('ocr', '')
        self.assertIn('卷北鿌沮渠蒙遜', ocr)
        self.assertIn('\U0002e34f', ocr)

    def test_format_rare(self):
        rare = '测[尸@工]试[仁-二+戾]一[少/兔]下[乳-孚+卓]看[束*束]看'
        txt = '测𡰱试㑦一㝹下𠃵看𣗥看'
        self.assertEqual(format_rare(rare), txt)

    def test_variant_normalize(self):
        variants = '鼶𪕬𪕧𪕽𪕻测𪕊𪕑䶅𪕘试𪕓𪕗看黑𪐫黒𪐗看'
        normal = normalize(variants)
        txt = '鼶鼶鼶鼶鼶測𪕊𪕊䶅䶅試𪕓𪕓看黑黑黑黑看'
        self.assertEqual(normal, txt)
