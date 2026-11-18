#!/usr/bin/env python3
"""Prepare a row-scoped 1688 link batch. Dry run by default; --fetch enables billing."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

ENDPOINT = 'https://api.sandbase.ai/v1/api/1688/item/detail-by-url'
GENERATED = 'title remark thumb images pro_fields content seo_title1 seo_desc file_name'.split()
REQUIRED = ['link', 'SANDBASE_API_KEY', 'IMGBB_API_KEY', *GENERATED]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def canonical(link):
    u = urlsplit(link.strip())
    if u.scheme not in ('https','http') or u.netloc.lower() != 'detail.1688.com':
        raise ValueError('Invalid 1688 detail URL')
    m = re.fullmatch(r'/offer/([1-9][0-9]{0,19})\.html/?', u.path)
    if not m:
        raise ValueError('Invalid offer ID')
    return m[1], 'https://detail.1688.com/offer/' + m[1] + '.html'


def fetch_item(url, key):
    body = json.dumps({'url':url, 'language':'zh'}).encode()
    req = Request(ENDPOINT, data=body, method='POST', headers={
        'Authorization':'Bearer '+key, 'Content-Type':'application/json', 'Accept':'application/json'})
    with build_opener(NoRedirect).open(req, timeout=45) as response:
        raw = response.read(8_000_001)
        if len(raw)>8_000_000:
            raise ValueError('Oversized response')
        return json.loads(raw)


def write_json(path, obj):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(template):
    with template.open(encoding='utf-8-sig',newline='') as f:
        it = csv.reader(f,strict=True)
        headers = next(it,[])
        if len(set(headers))!=len(headers) or not set(REQUIRED)<=set(headers) or any(h!=h.strip() or not h for h in headers):
            raise ValueError('Use the current link template with unique, exact field names')
        rows=[]
        for fields in it:
            if not fields: continue
            if len(fields)!=len(headers): raise ValueError('Malformed CSV record')
            rows.append(dict(zip(headers,fields)))
    return headers,rows


def prepare(template, run, fetch=False, request=fetch_item):
    headers,rows=read_rows(template)
    fingerprint=digest(template)
    dest=run/'batch-manifest.json'
    old=json.loads(dest.read_text()) if dest.exists() else {}
    if old and (old.get('input_mode')!='link_batch' or old.get('template_sha256')!=fingerprint):
        raise ValueError('Input changed: use a new batch directory')
    prev={p['product_id']:p for p in old.get('products',[])}
    m=dict(version=2,input_mode='link_batch',template_path=str(template.resolve()),template_sha256=fingerprint,
           headers=headers,template_rows=len(rows),config_mapping='positional',products=[],inputs=[])
    seen={}
    if fetch: run.mkdir(exist_ok=True,parents=True)
    for i,row in enumerate(rows,2):
        if not any(v.strip() for v in row.values()): continue
        entry={'template_row':i}
        try: offer,url=canonical(row['link'])
        except ValueError:
            m['inputs'].append(dict(entry,status='blocked',reason='Missing or unsupported 1688 offer link'));continue
        pid='offer-'+offer
        if offer in seen:
            m['inputs'].append(dict(entry,status='duplicate',duplicate_of=seen[offer],source_file=url));continue
        seen[offer]=i
        base=Path('products')/pid
        p=dict(entry,product_id=pid,source_file=url,product_file=str(base/'product.json'),source_data=str(base/'item.json'))
        m['products'].append(p); data_path=run/base/'item.json'; guard=run/base/'request-pending'
        key=row['SANDBASE_API_KEY'].strip()
        if data_path.exists():
            try:
                data=json.loads(data_path.read_text())
                if str(data['item_id'])!=offer or not data['title']: raise ValueError()
                sh=digest(data_path)
                if prev.get(pid,{}).get('source_sha256',sh)!=sh: raise ValueError()
                p.update(source_sha256=sh,status='ready' if prev.get(pid,{}).get('status')=='ready' else 'extracted')
            except (ValueError,KeyError,TypeError): p.update(status='blocked',reason='Cached item failed verification')
        elif guard.exists(): p.update(status='pending',reason='Check request history before any retry')
        elif not key: p.update(status='blocked',reason='This row has no SANDBASE_API_KEY')
        elif not fetch: p.update(status='planned')
        else:
            data_path.parent.mkdir(parents=True,exist_ok=True)
            # Exclusive checkpoint before sending; connection failures must never cause a silent second charge.
            with guard.open('x') as f: f.write('Check provider history before retrying.\n')
            try:
                result=request(url,key)
                outputs=result.get('outputs') if isinstance(result,dict) else result
                data=outputs[0]['data']
                if str(data['item_id'])!=offer or not data['title']: raise ValueError()
                serialized=json.dumps(data,ensure_ascii=False)
                if any(v and v in serialized for v in (key,row['IMGBB_API_KEY'].strip())): raise ValueError()
                write_json(data_path,data); p.update(status='extracted',source_sha256=digest(data_path));guard.unlink()
            except HTTPError as e:
                p.update(status='pending',reason=f'HTTP {e.code}; inspect request history')
            except (OSError,ValueError,TypeError,KeyError,IndexError):
                p.update(status='pending',reason='Result unverified; inspect request history')
        m['inputs'].append(dict(entry,product_id=pid,source_file=url,status=p['status']))
    if fetch: write_json(dest,m)
    return m


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--template-csv',type=Path,required=True); a.add_argument('--run-dir',type=Path,required=True)
    a.add_argument('--fetch',action='store_true',help='Make potentially billable SandBase calls')
    args=a.parse_args()
    try: manifest=prepare(args.template_csv,args.run_dir,args.fetch)
    except (OSError,ValueError,csv.Error) as e: a.exit(2, f'Invalid input or run directory ({type(e).__name__}).\n')
    for r in manifest['inputs']: print(f"row {r['template_row']}: {r['status']}")
    if not args.fetch: print('Dry run: no network calls or output writes.')
    raise SystemExit(2 if any(r['status'] in ('blocked','pending') for r in manifest['inputs']) else 0)
