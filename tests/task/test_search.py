#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase


class TestText(APITestCase):

    def test_search_cbeta(self):
        q = '教自觀身令心轉細，還教觀佛'
        r = self.fetch('/data/search_cbeta?q=%s&_no_auth=1' % q)
        self.assert_code(200, r)
