"""Exercise the row-to-request boundary without network access or real keys."""
import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_link_batch as links


class LinkBatch(unittest.TestCase):
    def setUp(self):
        td=TemporaryDirectory(); self.addCleanup(td.cleanup)
        self.root=Path(td.name); self.sheet=self.root/'input.csv'; self.run=self.root/'run'
        self.calls=[]
    def write(self, rows):
        with self.sheet.open('w',newline='') as f:
            w=csv.DictWriter(f,links.REQUIRED);w.writeheader()
            for url,key in rows:
                w.writerow(dict(link=url,SANDBASE_API_KEY=key,IMGBB_API_KEY='IMG-TEST-ONLY'))
    def request(self,url,key):
        self.calls.append((url,key))
        return {'outputs':[{'data':{'item_id':links.canonical(url)[0],'title':'Sample'}}]}
    def test_each_offer_uses_own_key_and_survives_blank_and_blocked_rows(self):
        a='https://detail.1688.com/offer/101.html'; b=a.replace('101','102')
        self.write([(a+'?share_token=private','SANDBASE-ROW-A'),(a.replace('101','103'),''),(a,'SANDBASE-DUPLICATE'),(b,'SANDBASE-ROW-B')])
        dry=links.prepare(self.sheet,self.run,False,self.request);self.assertFalse(self.run.exists());self.assertEqual(self.calls,[])
        self.assertEqual([r['status'] for r in dry['inputs']],['planned','blocked','duplicate','planned'])
        m=links.prepare(self.sheet,self.run,True,self.request)
        self.assertEqual(self.calls,[(a,'SANDBASE-ROW-A'),(b,'SANDBASE-ROW-B')])
        self.assertEqual([p['template_row'] for p in m['products']],[2,3,5])
        for f in self.run.rglob('*.json'):
            for secret in ('SANDBASE-ROW','IMG-TEST-ONLY','share_token'): self.assertNotIn(secret,f.read_text())
        links.prepare(self.sheet,self.run,True,self.request);self.assertEqual(len(self.calls),2)
    def test_pending_or_wrong_offer_never_retried_automatically(self):
        self.write([('https://detail.1688.com/offer/101.html','SANDBASE-KEY')])
        def wrong(url,key): return {'outputs':[{'data':{'item_id':999,'title':'wrong'}}]}
        self.assertEqual(links.prepare(self.sheet,self.run,True,wrong)['products'][0]['status'],'pending')
        links.prepare(self.sheet,self.run,True,self.request); self.assertFalse(self.calls)
    def test_key_sent_only_to_provider_with_canonical_body(self):
        url='https://detail.1688.com/offer/101.html'
        with patch.object(links,'build_opener') as op:
            op.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"outputs":[]}'
            links.fetch_item(url,'row-key')
            req=op.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url,links.ENDPOINT)
            self.assertEqual(req.get_header('Authorization'),'Bearer row-key')
            self.assertEqual(json.loads(req.data),{'url':url,'language':'zh'})
    def test_invalid_hosts_never_trigger_api(self):
        self.write([('https://detail.1688.com.other/offer/123.html','SANDBASE-KEY')])
        m=links.prepare(self.sheet,self.run,True,self.request)
        self.assertFalse(self.calls);self.assertEqual(m['inputs'][0]['status'],'blocked')
