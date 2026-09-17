import json
import unittest

from llmtier_v03.sse import frame, response_stream


def response(content=None,item=None):
    output=[item or {"type":"message","id":"msg_1","role":"assistant","status":"completed","content":[content or {"type":"output_text","text":"ok","annotations":[]}]}]
    return {"id":"resp_1","object":"response","created_at":1,"status":"completed","model":"Worker","output":output,"usage":{"input_tokens":1,"output_tokens":1,"total_tokens":2},"error":None}


def events(value):
    result=[]
    for chunk in response_stream(value):
        for line in chunk.decode().splitlines():
            if line.startswith("data: ") and line!="data: [DONE]":result.append(json.loads(line[6:]))
    return result


class SSETests(unittest.TestCase):
    def test_frame_has_event(self): self.assertTrue(frame("x",{"a":1}).startswith(b"event: x\n"))
    def test_done_marker(self): self.assertEqual(list(response_stream(response()))[-1],b"data: [DONE]\n\n")
    def test_sequence_is_monotonic(self): self.assertEqual([x["sequence_number"] for x in events(response())],list(range(5)))
    def test_created_is_first(self): self.assertEqual(events(response())[0]["type"],"response.created")
    def test_completed_is_last_event(self): self.assertEqual(events(response())[-1]["type"],"response.completed")
    def test_incomplete_terminal_is_preserved(self):
        value=response(); value["status"]="incomplete"; value["incomplete_details"]={"reason":"max_output_tokens"}
        self.assertEqual(events(value)[-1]["type"],"response.incomplete")
    def test_text_delta(self): self.assertEqual([x for x in events(response()) if x["type"]=="response.output_text.delta"][0]["delta"],"ok")
    def test_refusal_delta(self): self.assertEqual([x for x in events(response({"type":"refusal","refusal":"no"})) if x["type"]=="response.refusal.delta"][0]["delta"],"no")
    def test_function_arguments_done(self):
        item={"type":"function_call","id":"fc_1","call_id":"c","name":"f","arguments":"{}","status":"completed"}; types=[x["type"] for x in events(response(item=item))];self.assertIn("response.function_call_arguments.done",types)
