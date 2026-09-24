import os
import unittest
from unittest.mock import patch

from http_api.auth import authenticate, unauthenticated_principal
from http_api.errors import ApiError


class Headers(dict):
    def get(self,key,default=None):return super().get(key,default)


class AuthTests(unittest.TestCase):
    def test_missing_config_is_503(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaises(ApiError) as cm:authenticate(Headers(),"data")
        self.assertEqual(cm.exception.status,503)
    def test_missing_bearer_is_401(self):
        with patch.dict(os.environ,{"LLMTIER_DATA_TOKEN":"x"},clear=True),self.assertRaises(ApiError) as cm:authenticate(Headers(),"data")
        self.assertEqual(cm.exception.status,401)
    def test_wrong_token_is_403(self):
        with patch.dict(os.environ,{"LLMTIER_DATA_TOKEN":"x"},clear=True),self.assertRaises(ApiError) as cm:authenticate(Headers(Authorization="Bearer y"),"data")
        self.assertEqual(cm.exception.status,403)
    def test_data_token(self):
        with patch.dict(os.environ,{"LLMTIER_DATA_TOKEN":"x"},clear=True):self.assertEqual(authenticate(Headers(Authorization="Bearer x"),"data").role,"data")
    def test_admin_token(self):
        with patch.dict(os.environ,{"LLMTIER_ADMIN_TOKEN":"a"},clear=True):self.assertEqual(authenticate(Headers(Authorization="Bearer a"),"admin").role,"admin")
    def test_principal_header(self):
        with patch.dict(os.environ,{"LLMTIER_DATA_TOKEN":"x"},clear=True):self.assertEqual(authenticate(Headers(Authorization="Bearer x",**{"X-Principal-ID":"p"}),"data").principal_id,"p")
    def test_dev_token(self):
        with patch.dict(os.environ,{"LLMTIER_DEV_MODE":"1"},clear=True):self.assertEqual(authenticate(Headers(Authorization="Bearer dev-data"),"data").principal_id,"consumer")
    def test_loopback_dev_mode_is_limited_to_loopback(self):
        with patch.dict(os.environ,{"LLMTIER_DEV_MODE":"1"},clear=True):
            self.assertEqual(unauthenticated_principal("127.0.0.1",Headers(),"admin").principal_id,"loopback-operator")
            self.assertEqual(unauthenticated_principal("192.168.1.20",Headers(),"admin").principal_id,"trusted-lan-operator")
    def test_trusted_lan_mode_accepts_private_addresses(self):
        self.assertEqual(unauthenticated_principal("192.168.1.20",Headers(),"admin").principal_id,"trusted-lan-operator")
        self.assertEqual(unauthenticated_principal("10.0.0.7",Headers(),"data").principal_id,"trusted-lan-consumer")
        self.assertEqual(unauthenticated_principal("fd00::7",Headers(),"data").principal_id,"trusted-lan-consumer")
        self.assertIsNone(unauthenticated_principal("8.8.8.8",Headers(),"admin"))
    def test_explicit_bearer_disables_no_auth_path(self):
        self.assertIsNone(unauthenticated_principal("192.168.1.20",Headers(Authorization="Bearer x"),"admin"))
