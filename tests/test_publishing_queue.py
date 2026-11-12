import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

p=Path(__file__).resolve().parents[1]/"scripts"/"publishing_queue.py"
s=importlib.util.spec_from_file_location("publishing_queue",p)
q=importlib.util.module_from_spec(s)
s.loader.exec_module(q)

def example(**updates):
    v=dict(id="orbiuno-20261112-extra",account="orbiuno",platform="instagram",
        media_url="https://example.org/photo.jpg",source_url="https://example.org/news",
        caption="Verified technology news with a proper original source.",
        rights_confirmed=True,scheduled_at="2026-11-12T15:00:00-05:00",status="scheduled")
    v.update(updates)
    return v

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"queue.json"
    def tearDown(self): self.tmp.cleanup()
    def set_posts(self,*posts):self.path.write_text(json.dumps({"posts":list(posts)}),encoding="utf-8")
    def test_post_once(self):
        self.set_posts(example())
        calls=[]
        def sender(p):calls.append(p["id"]);return {"media_id":"123","permalink":"https://instagram.com/p/123/"}
        at=dt.datetime(2026,11,12,22,tzinfo=dt.timezone.utc)
        self.assertEqual(q.run(self.path,sender,at=at)[0]["status"],"published")
        self.assertEqual(q.run(self.path,sender,at=at),[])
        self.assertEqual(len(calls),1)
    def test_rights_block(self):
        self.set_posts(example(rights_confirmed=False))
        events=q.run(self.path,lambda p:self.fail("sent"),at=dt.datetime(2026,11,12,22,tzinfo=dt.timezone.utc))
        self.assertEqual(events[0]["status"],"needs_review")
    def test_unknown_result_never_retries(self):
        self.set_posts(example())
        def failing(_):raise TimeoutError("unknown")
        at=dt.datetime(2026,11,12,22,tzinfo=dt.timezone.utc)
        self.assertEqual(q.run(self.path,failing,at=at)[0]["status"],"needs_review")
        self.assertEqual(q.run(self.path,failing,at=at),[])
    def test_future(self):
        self.set_posts(example(scheduled_at="2026-11-14T15:00:00-05:00"))
        self.assertEqual(q.run(self.path,lambda p:self.fail("sent"),at=dt.datetime(2026,11,12,22,tzinfo=dt.timezone.utc)),[])
    def test_no_source(self):
        self.set_posts(example(source_url="invalid"))
        with self.assertRaises(ValueError):q.load(self.path)
if __name__=="__main__":unittest.main()
