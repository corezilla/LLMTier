from __future__ import annotations

import unittest
from unittest.mock import patch

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


class ProbeAdapter:
    def __init__(self,*_):pass
    def probe(self):return True


class AdminTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.admin=self.fx.app.admin
    def tearDown(self):self.fx.close()
    def test_page_shape(self):
        page=self.admin.page([{"id":"a"}],"operator","x");self.assertEqual(page["data"],[{"id":"a"}])
    def test_page_limit(self):
        page=self.admin.page([{"id":str(i)} for i in range(3)],"operator","x",limit=2);self.assertTrue(page["page"]["has_more"])
    def test_page_cursor(self):
        first=self.admin.page([{"id":str(i)} for i in range(3)],"operator","x",limit=2);second=self.admin.page([],"operator","x",first["page"]["next_cursor"],2);self.assertEqual(second["data"][0]["id"],"2")
    def test_cursor_principal_bound(self):
        first=self.admin.page([{"id":"1"},{"id":"2"}],"a","x",limit=1)
        with self.assertRaises(ApiError):self.admin.page([],"b","x",first["page"]["next_cursor"],limit=1)
    def test_first_page_snapshot_is_frozen(self):
        # The first page freezes the source set; later pages must serve the
        # frozen screen even if the live data changes in between.
        data=[{"id":str(i),"value":"original"} for i in range(3)]
        first=self.admin.page(data,"operator","frozen",limit=2)
        self.assertEqual([r["id"] for r in first["data"]],["0","1"])
        self.assertTrue(first["page"]["has_more"])
        data[2]["value"]="changed"
        data.append({"id":"9","value":"new"})
        second=self.admin.page(data,"operator","frozen",first["page"]["next_cursor"],limit=2)
        self.assertEqual([r["id"] for r in second["data"]],["2"])
        self.assertEqual(second["data"][0]["value"],"original")


import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


START="2000-01-01T00:00:00Z";END="2100-01-01T00:00:00Z"


class UsageTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.u=self.fx.app.usage
    def tearDown(self):self.fx.close()
    def record(self,rid="r1",usage=None):self.u.authorize_dispatch("p",rid,"Worker","/v1/responses");self.u.finish("p",rid,usage)
    def test_snapshot_is_stable(self):
        self.record("r1",{"input_tokens":1,"output_tokens":1,"total_tokens":2});page=self.u.page("p",None,limit=1,since=START,until=END);self.record("r2",{"input_tokens":1,"output_tokens":1,"total_tokens":2});old=self.u.page("p",page["snapshot_id"]+":0",limit=10,since=START,until=END);self.assertEqual(len(old["data"]),1)
    def test_cursor_filter_mismatch(self):
        self.record();page=self.u.page("p",None,since=START,until=END)
        with self.assertRaises(ApiError):self.u.page("p",page["snapshot_id"]+":0",since="2001-01-01T00:00:00Z",until=END)
    def test_invalid_window(self):
        with self.assertRaises(ApiError):self.u.page("p",None,since=END,until=START)
