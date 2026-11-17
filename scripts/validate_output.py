#!/usr/bin/env python3
"""Validate English product fields, image provenance, local files and detail exports."""
import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlparse

GENERATED = 'title remark pro_fields content seo_title1 seo_desc file_name thumb scenario_image images'.split()
HEADERS = ['link', 'template', 'IMGBB_API_KEY'] + GENERATED
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]')


class HTMLImages(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.images = []
        self.unsafe = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            self.images.append((a.get('src', ''), a.get('alt', '')))
        if tag in ('script', 'iframe', 'object', 'embed') or any(k.startswith('on') for k in a):
            self.unsafe = True


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        rows = list(r)
        return r.fieldnames or [], rows


def direct(value):
    u = urlparse(value)
    return (u.scheme == 'https' and u.hostname == 'i.ibb.co' and not u.username
            and not u.password and not u.query and not u.fragment and u.path.endswith('.webp'))


def local_file(root, value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] != 'images':
        return None
    target = (root / p).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file() or target.suffix != '.webp':
        return None
    data = target.read_bytes()
    return target if data[:4] == b'RIFF' and data[8:12] == b'WEBP' else None


def validate(csv_path, mode, manifest_path, original=None, batch_manifest=None):
    root = csv_path.parent
    errors = []
    raw = csv_path.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        errors.append('UTF-8 BOM in output may corrupt the first header; export UTF-8 without BOM')
    try:
        with csv_path.open(encoding='utf-8', newline='') as f:
            parsed = list(csv.reader(f, strict=True))
    except (UnicodeDecodeError, csv.Error):
        return errors + ['Output is not valid UTF-8 CSV'], 0
    plain_headers = parsed[0] if parsed else []
    if len(plain_headers) != len(set(plain_headers)):
        errors.append('Duplicate CSV headers')
    if any(h != h.strip() or re.search(r'[\ufeff\u200b-\u200d\u2060\r\n]', h) for h in plain_headers):
        errors.append('CSV header contains whitespace or invisible characters')
    for n, cells in enumerate(parsed[1:], 2):
        if len(cells) != len(plain_headers):
            errors.append(f'row {n}: CSV field count differs from header count')
    if set(GENERATED) - set(plain_headers):
        errors.append('Raw UTF-8 parser cannot match every required header exactly')
    # Output must have template-compatible plain field identifiers. Input templates may have BOM.
    if plain_headers and all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', h) for h in plain_headers):
        if raw.split(b'\n', 1)[0].rstrip(b'\r').decode('utf-8') != ','.join(plain_headers):
            errors.append('Use unquoted field names in the header to match the website template')
    if errors:
        return errors, max(len(parsed) - 1, 0)
    headers, rows = read_csv(csv_path)
    def fail(n, message): errors.append(f'row {n}: {message}')
    missing = set(GENERATED) - set(headers)
    if missing: errors.append('Missing headers: ' + ', '.join(sorted(missing)))
    if not rows: errors.append('No product rows; a template is not a completed product export')
    products = json.loads(manifest_path.read_text(encoding='utf-8')).get('products', [])
    records = {x['file_name']: x for x in products}
    if len(records) != len(products): errors.append('Duplicate product slugs in image manifest')
    seen = set()
    for n, row in enumerate(rows, 2):
        for field in GENERATED:
            value = row.get(field) or ''
            if not value.strip() and field != 'scenario_image': fail(n, f'{field} is empty')
            if CJK.search(html.unescape(value)): fail(n, f'{field} contains Chinese text')
            if re.search(r'\b(?:Xinbada|Lifeworth|ZHENGFENG)\b', value, re.I):
                fail(n, f'{field} contains inherited branding')
        slug = row.get('file_name', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            fail(n, 'Invalid ASCII product slug')
            continue
        if slug in seen: fail(n, 'Duplicate product slug')
        seen.add(slug)
        if row.get('seo_title1') != row.get('title'): fail(n, 'SEO title differs from title')
        if row.get('seo_desc') != row.get('remark'): fail(n, 'SEO description differs from remark')
        if any(re.match(r'^\s*(?:[•●▪*+\-]|\d+[.)])\s*', s) for s in row.get('pro_fields', '').splitlines()):
            fail(n, 'pro_fields has leading bullets or numbering')
        content = row.get('content', '')
        if re.search(r'\{\{.+?\}\}|\bTODO\b|\bPLACEHOLDER\b', content): fail(n, 'Unfilled content template')
        parsed = HTMLImages(content)
        if parsed.unsafe: fail(n, 'Executable or embedded content is not allowed')
        pairs = []
        for line in row.get('images', '').splitlines():
            if not line.strip(): continue
            if '|' not in line:
                fail(n, 'Gallery line lacks URL|alt separator')
                continue
            pairs.append(tuple(x.strip() for x in line.split('|', 1)))
        if not pairs: fail(n, 'No gallery images')
        if pairs and row.get('thumb') != pairs[0][0]: fail(n, 'Cover is not the first gallery image')
        if len(set(url for url, _ in pairs)) != len(pairs): fail(n, 'Duplicate gallery image references')
        gallery_urls = {url for url, _ in pairs}
        detail_entries = records.get(slug, {}).get('detail_images', [])
        detail_urls = [e.get('direct_url' if mode == 'remote' else 'path', '') for e in detail_entries]
        if len(set(detail_urls)) != len(detail_urls): fail(n, 'Duplicate detail asset references')
        if gallery_urls.intersection(detail_urls): fail(n, 'Shared gallery assets must not be duplicated in detail_images')
        allowed = gallery_urls | set(detail_urls)
        if row.get('scenario_image') and row['scenario_image'] not in gallery_urls:
            fail(n, 'scenario_image is outside the product gallery')
        if not parsed.images or parsed.images[0][0] != row.get('thumb'):
            fail(n, 'First detail image is not the cover')
        for url, alt in pairs + parsed.images:
            if not alt or CJK.search(alt): fail(n, 'Missing or non-English image alt')
            if url not in allowed: fail(n, 'Detail image has no approved asset provenance')
            if mode == 'remote' and not direct(url): fail(n, 'Image must be an ImgBB WebP Direct link')
            if mode == 'local' and not local_file(root, url): fail(n, 'Local WebP missing or unsafe path')
        entries = records.get(slug, {}).get('images', [])
        if len(entries) != len(pairs): fail(n, 'Image manifest count differs from gallery')
        for i, (entry, pair) in enumerate(zip(entries, pairs)):
            if entry.get('direct_url' if mode == 'remote' else 'path') != pair[0]: fail(n, 'Manifest order/URL mismatch')
            if entry.get('alt') != pair[1]: fail(n, 'Manifest alt differs from gallery')
            if not entry.get('source'): fail(n, 'Missing original image source')
            if entry.get('visual_reviewed') is not True or entry.get('product_match') is not True:
                fail(n, 'Image visual/product verification is incomplete')
            if not local_file(root, entry.get('path', '')): fail(n, 'Manifest local WebP is missing')
            if i == 0:
                if entry.get('role') != 'cover' or entry.get('origin') != 'generated_cover':
                    fail(n, 'First image must be a generated cover')
            elif (entry.get('role') != 'gallery' or entry.get('white_background') is not True
                  or entry.get('origin') not in ('source_white', 'background_edited', 'text_localized')):
                fail(n, 'Gallery image is not a verified source-derived white-background image')
        used_detail_urls = {url for url, _ in parsed.images}
        for entry, url in zip(detail_entries, detail_urls):
            if entry.get('role') not in ('detail_photo', 'production', 'material', 'application', 'drawing'):
                fail(n, 'Invalid detail asset role')
            if entry.get('origin') not in ('source_detail', 'text_localized', 'background_edited'):
                fail(n, 'Detail asset must come from the supplied product PDF')
            if not entry.get('source') or not entry.get('source_pages') or not entry.get('context'):
                fail(n, 'Detail asset needs PDF provenance and context')
            if entry.get('visual_reviewed') is not True or entry.get('context_reviewed') is not True:
                fail(n, 'Detail asset visual/context verification is incomplete')
            if not entry.get('alt') or CJK.search(entry['alt']): fail(n, 'Detail asset needs English alt')
            if not local_file(root, entry.get('path', '')): fail(n, 'Detail asset local WebP is missing')
            if mode == 'remote' and not direct(url): fail(n, 'Detail asset must have an ImgBB WebP Direct link')
            if url not in used_detail_urls: fail(n, 'Approved detail asset is not used in the content')
        folder = root / 'images' / slug
        if folder.exists() and any(x.is_file() and x.suffix != '.webp' for x in folder.iterdir()):
            fail(n, 'Final image folder includes non-WebP files')
        for suffix in ('.fragment.html', '.html', '.txt'):
            path = root / 'details' / (slug + suffix)
            if not path.is_file() or not path.stat().st_size: fail(n, 'Missing independent detail export ' + suffix)
            elif CJK.search(html.unescape(path.read_text(encoding='utf-8'))): fail(n, 'Detail export contains Chinese text')
        fragment = root / 'details' / (slug + '.fragment.html')
        if fragment.is_file() and fragment.read_text(encoding='utf-8').strip() != content.strip():
            fail(n, 'Detail fragment differs from CSV content')
        page = root / 'details' / (slug + '.html')
        if page.is_file():
            page_text = page.read_text(encoding='utf-8')
            if not re.search(r'<html\b[^>]*\blang=[\"\']en[\"\']', page_text, re.I):
                fail(n, 'Standalone detail page needs lang=en')
            if not re.search(r'<meta\b[^>]*\bname=[\"\']viewport[\"\']', page_text, re.I):
                fail(n, 'Standalone detail page needs a viewport meta tag')
            for url, alt in HTMLImages(page_text).images:
                if mode == 'remote':
                    if url not in allowed: fail(n, 'Standalone detail image has no approved asset provenance')
                else:
                    resolved = (page.parent / url).resolve()
                    expected = {(root / value).resolve() for value in allowed}
                    if resolved not in expected or not resolved.is_file():
                        fail(n, 'Standalone detail has an invalid relative image reference')
    if original:
        old_headers, old_rows = read_csv(original)
        if headers != old_headers: errors.append('Original/output column names or order differ')
        if len(old_rows) != len(rows): errors.append('Original/output row count differs')
        for n, (old, new) in enumerate(zip(old_rows, rows), 2):
            for key in old_headers:
                if key not in GENERATED and old.get(key) != new.get(key):
                    fail(n, f'Read-only input field changed: {key}')
    if batch_manifest:
        batch = json.loads(batch_manifest.read_text(encoding='utf-8'))
        template = Path(batch['template_path'])
        template_headers, template_rows = read_csv(template)
        if hashlib.sha256(template.read_bytes()).hexdigest() != batch['template_sha256']:
            errors.append('Batch template changed since preparation')
        if headers != template_headers or headers != batch['headers']:
            errors.append('PDF batch column names or order differ from the input template')
        ready = [p for p in batch['products'] if p['status'] == 'ready']
        if len(ready) != len(rows): errors.append('Output count differs from ready PDF count')
        for n, (product, row) in enumerate(zip(ready, rows), 2):
            record_path = (batch_manifest.parent / product['product_file']).resolve()
            if not record_path.is_relative_to(batch_manifest.parent.resolve()):
                fail(n, 'Product file escapes the batch directory')
                continue
            record = json.loads(record_path.read_text(encoding='utf-8'))
            if record.get('source_sha256') != product.get('source_sha256') or record.get('reviewed') is not True:
                fail(n, 'Product source or review does not match the PDF')
            config_number = product.get('template_row')
            config = template_rows[config_number - 2] if isinstance(config_number, int) and 2 <= config_number <= len(template_rows) + 1 else {}
            if template_rows and not config: fail(n, 'Invalid template configuration mapping')
            for key in headers:
                expected = (record.get('row', {}).get(key, '') if key in GENERATED else
                            record.get('verified_source_url', '') if key == 'link' else config.get(key, ''))
                if row.get(key, '') != expected:
                    fail(n, 'PDF product or template configuration differs in field: ' + key)
    return errors, len(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv_file', type=Path)
    p.add_argument('--mode', choices=['local', 'remote'], required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--original', type=Path)
    p.add_argument('--batch-manifest', type=Path, help='Validate PDF-to-output mapping and template configuration')
    args = p.parse_args()
    errors, count = validate(args.csv_file, args.mode, args.manifest, args.original, args.batch_manifest)
    for error in errors: print('ERROR: ' + error)
    if errors: return 1
    print(f'OK: {count} product rows; {args.mode} structural checks passed; factual and visual review remains required')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
