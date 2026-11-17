#!/usr/bin/env python3
"""Upload reviewed WebP files with per-file checkpoints and no automatic retries."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def direct_url(value):
    p = urlparse(value)
    return (p.scheme == 'https' and p.hostname == 'i.ibb.co'
            and not p.username and not p.password and not p.query and not p.fragment
            and p.path.lower().endswith('.webp'))


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    temp.replace(path)


def upload(path, key, timeout):
    boundary = '----Yiyiyi' + secrets.token_hex(16)
    filename = path.name.replace('"', '').replace('\r', '').replace('\n', '')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n'.encode()
            + key.encode() + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: image/webp\r\n\r\n'.encode()
            + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode())
    req = Request('https://api.imgbb.com/1/upload', data=body, method='POST', headers={
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
        'Accept': 'application/json', 'User-Agent': 'yiyiyi-1688-product-import/1.0'})
    with urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    url = payload.get('data', {}).get('url', '')
    if not payload.get('success') or not direct_url(url):
        raise ValueError('Upload response has no valid WebP Direct link')
    return url


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image_dir', type=Path)
    p.add_argument('--csv-file', type=Path, required=True)
    p.add_argument('--row-number', type=int, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--timeout', type=float, default=45)
    p.add_argument('--dry-run', action='store_true', help='Validate files and row without any network call')
    p.add_argument('--retry-pending', action='store_true', help='Explicitly retry uncertain prior uploads after review')
    args = p.parse_args()
    if args.row_number < 2 or args.timeout <= 0:
        p.error('Row number must be >= 2 and timeout must be positive')
    with args.csv_file.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if args.row_number - 2 >= len(rows):
        p.error(f'CSV row {args.row_number} does not exist')
    key = (rows[args.row_number - 2].get('IMGBB_API_KEY') or '').strip()
    if not key:
        print(f'ERROR: missing upload credential at row {args.row_number}', file=sys.stderr)
        return 2
    images = sorted(args.image_dir.glob('*.webp'))
    if not images:
        p.error('No WebP images found')
    hashes = {}
    for path in images:
        data = path.read_bytes()
        if not (data[:4] == b'RIFF' and data[8:12] == b'WEBP') or len(data) > 32_000_000:
            p.error('Invalid or oversized WebP file')
        hashes[path.name] = hashlib.sha256(data).hexdigest()
    if args.dry_run:
        print(f'OK: row {args.row_number}, {len(images)} WebP files; no upload performed')
        return 0
    state = {'provider': 'ImgBB', 'complete': False, 'files': {}}
    if args.manifest.exists():
        state = json.loads(args.manifest.read_text(encoding='utf-8'))
    state['complete'] = False
    for path in images:
        old = state['files'].get(path.name, {})
        same = old.get('sha256') == hashes[path.name]
        if same and old.get('status') == 'uploaded' and direct_url(old.get('direct_url', '')):
            continue
        if same and old.get('status') == 'pending' and not args.retry_pending:
            print('STOP: an earlier upload has an uncertain result; review before --retry-pending', file=sys.stderr)
            return 1
        state['files'][path.name] = {'sha256': hashes[path.name], 'status': 'pending'}
        save(args.manifest, state)
        try:
            url = upload(path, key, args.timeout)
        except Exception:
            # Never emit response bodies, exception URLs, credentials, or delete links.
            print('STOP: upload did not return a verified success; checkpoint preserved', file=sys.stderr)
            return 1
        state['files'][path.name].update(status='uploaded', direct_url=url)
        save(args.manifest, state)
    state['complete'] = True
    state['ordered_files'] = [x.name for x in images]
    save(args.manifest, state)
    print(f'OK: {len(images)} uploads verified; manifest saved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
