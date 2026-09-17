import os
import unittest
from unittest.mock import patch

from llmtier_v03.auth import authenticate
from llmtier_v03.errors import ApiError


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
