import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from http_api.errors import ApiError
from inference.providers.openai import OpenAIProvider


class FakeResponse:
    def __init__(self, body, content_type="application/json", status=200):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.body


class OpenAIProviderTests(unittest.TestCase):
    def test_probe_uses_authenticated_models_endpoint(self):
        with tempfile.TemporaryDirectory() as root:
            secret=Path(root)/"key"; secret.write_text("secret-value")
            seen={}
            def open_url(req, timeout, **kwargs):
                seen["url"],seen["auth"]=req.full_url,req.headers.get("Authorization")
                return FakeResponse(json.dumps({"object":"list","data":[]}))
            with patch("urllib.request.urlopen",side_effect=open_url):
                self.assertTrue(OpenAIProvider("https://provider.example",f"file:{secret}").probe())
            self.assertEqual(seen["url"],"https://provider.example/models")
            self.assertEqual(seen["auth"],"Bearer secret-value")

    def test_incomplete_terminal_is_preserved(self):
        response={"status":"incomplete","output":[],"usage":{"input_tokens":1,"output_tokens":2,"total_tokens":3},"error":None,"incomplete_details":{"reason":"max_output_tokens"}}
        stream=f"event: response.incomplete\ndata: {json.dumps({'type':'response.incomplete','response':response})}\n\ndata: [DONE]\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(stream,"text/event-stream")):
            result=OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(result.status,"incomplete")
        self.assertEqual(result.incomplete_details,{"reason":"max_output_tokens"})

    def test_duplicate_terminal_is_rejected(self):
        response={"status":"completed","output":[],"usage":None}
        event=f"event: response.completed\ndata: {json.dumps({'type':'response.completed','response':response})}\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(event+event,"text/event-stream")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(caught.exception.code,"provider_contract_error")

    def test_terminal_event_status_mismatch_is_rejected(self):
        response={"status":"incomplete","output":[],"usage":None}
        stream=f"event: response.completed\ndata: {json.dumps({'type':'response.completed','response':response})}\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(stream,"text/event-stream")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(caught.exception.code,"provider_contract_error")
