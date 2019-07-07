#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestText(APITestCase):

    def test_view_search_cbeta(self):
        q = '夫宗極絕於稱謂，賢聖以之沖默；玄旨非言'
        r = self.fetch('/data/search_cbeta?q=%s&_no_auth=1' % q)
        self.assert_code(200, r)

