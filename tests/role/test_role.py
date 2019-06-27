#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests.testcase import APITestCase
from controller import role
from controller import validate as v


class TestRole(APITestCase):
    def test_func(self):
        self.assertTrue(role.can_access('切分专家', '/task/do/block_cut_proof/GL_1_1_1', 'GET'))
        self.assertFalse(role.can_access('', '/task/do/block_cut_proof/GL_1_1_1', 'GET'))

        self.assertEqual(role.get_route_roles('/task/do/block_cut_proof/GL_1_1', 'GET'), ['切栏校对员', '切分专家'])

        routes = role.get_role_routes('切分专家, 数据管理员')
        self.assertIn('/api/task/page/@page_name', routes)
        self.assertIn('/data/page', routes)

    def test_validate(self):
        data = {'name': '1234567890', 'phone': '', 'email': '', 'password': '', 'age': 8}
        rules = [
            (v.allowed_keys, 'name', 'phone', 'email', 'password'),
            (v.not_empty, 'name', 'password'),
            (v.not_both_empty, 'phone', 'email'),
            (v.is_name, 'name'),
            (v.is_phone, 'phone'),
            (v.is_email, 'email'),
            (v.is_password, 'password'),
            (v.between, 'age', 10, 100),
        ]

        errs = v.validate(data, rules)
        self.assertEqual(set(errs.keys()), {'age', 'email', 'name', 'password', 'phone'})
        for k, t in errs.items():
            self.assertIs(t.__class__, tuple)
            self.assertIs(t[0].__class__, int)
            self.assertIs(t[1].__class__, str)
