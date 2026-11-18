#!/usr/bin/env python3
"""Validate English product fields, image provenance, local files and detail exports."""
import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
from PIL import Image
import re
from urllib.parse import urlparse, urlsplit

GENERATED = 'title remark pro_fields content seo_title1 seo_desc file_name thumb images'.split()
HEADERS = ['link', 'template', 'SANDBASE_API_KEY','IMGBB_API_KEY'] + GENERATED
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]')
LEGACY_BRAND = re.compile(r'(?<![\w-])YY(?![\w-])', re.I)


class HTMLImages(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.images = []
        self.unsafe = False
        self.has_legacy_brand = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            self.images.append((a.get('src', ''), a.get('alt', '')))
        if any(LEGACY_BRAND.search(a.get(key) or '') for key in ('alt', 'title', 'aria-label')):
            self.has_legacy_brand = True
        if tag in ('script', 'iframe', 'object', 'embed') or any(k.startswith('on') for k in a):
            self.unsafe = True

    def handle_data(self, data):
        if self.cdata_elem not in ('style', 'script') and LEGACY_BRAND.search(data):
            self.has_legacy_brand = True


class HTMLFAQ(HTMLParser):
    """Read marked FAQ pairs and verify that FAQ is the final visible content."""
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

    def __init__(self, text):
        super().__init__()
        self.stack = []
        self.sections = 0
        self.items = []
        self.last_visible_in_faq = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        parent = self.stack[-1] if self.stack else {}
        frame = {'tag': tag, 'faq': parent.get('faq', False),
                 'item': parent.get('item'), 'field': parent.get('field'),
                 'hidden': parent.get('hidden', False) or tag in ('style','script','head')}
        if 'data-product-faq' in a:
            self.sections += 1
            frame['faq'] = True
        if 'data-faq-item' in a and frame['faq']:
            item = {'question': '', 'answer': '', 'question_count': 0, 'answer_count': 0}
            self.items.append(item)
            frame['item'] = item
        for field in ('question', 'answer'):
            if 'data-faq-' + field in a and frame['item'] is not None:
                frame['field'] = field
                frame['item'][field + '_count'] += 1
        if tag in ('img', 'video', 'audio', 'hr') and not frame['hidden']:
            self.last_visible_in_faq = frame['faq']
        if tag not in self.VOID:
            self.stack.append(frame)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        frame = self.stack[-1] if self.stack else {}
        if data.strip() and not frame.get('hidden'):
            self.last_visible_in_faq = frame.get('faq', False)
            if frame.get('item') is not None and frame.get('field'):
                frame['item'][frame['field']] += data


def faq_errors(content):
    faq = HTMLFAQ(content)
    errors = []
    if faq.sections != 1:
        errors.append('Exactly one marked product FAQ section is required')
    if len(faq.items) != 6:
        errors.append('Product FAQ must contain exactly 6 question/answer pairs')
    questions = []
    for item in faq.items:
        if any(item[f + '_count'] != 1 or not item[f].strip() for f in ('question','answer')):
            errors.append('Each FAQ item needs one non-empty question and one non-empty answer')
        questions.append(re.sub(r'\W+', '', item['question'].casefold()))
    if len(set(questions)) != len(questions):
        errors.append('FAQ questions must be distinct')
    if not faq.last_visible_in_faq:
        errors.append('Product FAQ must be the final visible detail content')
    return errors


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


ASSETS = Path(__file__).resolve().parents[1] / 'assets'
OFFICIAL_LOGO_HASH = hashlib.sha256((ASSETS / 'yiant-logo.png').read_bytes()).hexdigest()
COMPANY_HTML = (ASSETS / 'company-intro.html').read_text().strip()
REPORT_HTML = (ASSETS / 'material-reports.html').read_text().strip()
REPORT_HOST = 'https://yyy.szsdzx.com'


def check_reports(content, standalone=False):
    fragment = content.replace('src="'+REPORT_HOST+'/uploadfile/', 'src="/uploadfile/') if standalone else content
    canonical = re.sub(r'\s+', ' ', REPORT_HTML)
    flat = re.sub(r'\s+', ' ', fragment)
    errors = []
    company = re.sub(r'>\s+<', '><', COMPANY_HTML)
    compact = re.sub(r'>\s+<', '><', flat)
    if (compact.count('class="epd-company-intro"') != 1
            or company + '<section class="epd-product-section">' not in compact):
        errors.append('The Company Introduction heading and official company paragraphs must immediately precede the report section')
    if flat.count(canonical)!=1 or flat.count('class="epd-product-section"')!=1:
        errors.append('Exactly one official English insulation-paper report section is required')
    elif not re.match(r'\s*<section\b[^>]*\bdata-product-faq=["\']true["\']', flat.split(canonical,1)[1],re.I):
        errors.append('Official reports must precede the product FAQ')
    if re.search(r'<section\b[^>]*\bid=["\']ordering["\']|Buying notes\s*(?:&amp;|&)\s*precautions',fragment,re.I):
        errors.append('Retired ordering terms found')
    return errors


class SectionImages(HTMLParser):
    """Group images by their nearest section, including images in separate rows."""
    def __init__(self, content):
        super().__init__()
        self.stack, self.groups = [], []
        self.layout_errors = []
        self.in_header = 0
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'section':
            self.groups.append((a.get('id') or str(len(self.groups)+1), []))
            self.stack.append(self.groups[-1])
        elif tag == 'img' and self.stack:
            self.stack[-1][1].append(a.get('src',''))
        elif tag == 'header':
            self.in_header += 1
        elif tag == 'figcaption' and self.stack and self.stack[-1][0] == 'production':
            self.layout_errors.append('Production photos must have no captions')

    def handle_endtag(self, tag):
        if tag == 'section' and self.stack:
            self.stack.pop()
        elif tag == 'header' and self.in_header:
            self.in_header -= 1

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] == 'production' and not self.in_header and data.strip():
            if 'Production grid must contain images only' not in self.layout_errors:
                self.layout_errors.append('Production grid must contain images only')


def section_size_errors(content, files):
    sections = SectionImages(content)
    errors = sections.layout_errors
    for name, urls in sections.groups:
        if len(urls) < 2: continue
        sizes = set()
        for url in set(urls):
            f = files.get(url)
            if not f: continue  # Unregistered or missing assets have separate errors.
            try:
                with Image.open(f) as im: sizes.add(im.size)
            except OSError:
                errors.append('Cannot decode section image: '+name)
        if len(sizes)>1: errors.append('Different image dimensions in section: '+name)
    return errors


def expected_product_fields(text, title):
    """Read current or previously reviewed parameter lines for a batch-record comparison."""
    names, attributes = [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        pair = re.split(r'[:：]', line, maxsplit=1)
        if len(pair) != 2 or not all(part.strip() for part in pair):
            return None
        label, value = (part.strip() for part in pair)
        if label.casefold() in ('product name', 'product'):
            names.append(value)
        else:
            attributes.append(label + '：' + value)
    if len(set(names)) > 1:
        return None
    return '\n'.join(['Product Name\t：' + (names[0] if names else title), *attributes])


def generated_artwork_errors(entry, review_required=False):
    label = entry.get('source_ai_label')
    illustrated = entry.get('origin') == 'source_based_illustration'
    if label is None and not illustrated:
        if entry.get('generated_label_absent_reviewed', not review_required) is not True:
            return ['Generated artwork has an incomplete visible-label review']
        return []
    errors = []
    if not isinstance(label, str) or not label.strip():
        errors.append('Record the visible AI label from the original source')
    if not re.fullmatch(r'[a-f0-9]{64}', str(entry.get('source_sha256', ''))):
        errors.append('AI-labeled artwork needs the original image hash')
    if not (illustrated or entry.get('origin') == 'generated_cover'):
        errors.append('AI-labeled artwork needs a source-based illustration or generated cover')
    if entry.get('generated_label_absent_reviewed') is not True:
        errors.append('Generated artwork has an incomplete visible-label review')
    return errors


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
    if 'scenario_image' in headers: errors.append('Retired scenario_image field found in output')
    if not rows: errors.append('No product rows; a template is not a completed product export')
    products = json.loads(manifest_path.read_text(encoding='utf-8')).get('products', [])
    records = {x['file_name']: x for x in products}
    if len(records) != len(products): errors.append('Duplicate product slugs in image manifest')
    seen = set()
    for n, row in enumerate(rows, 2):
        if any(row.get(key) for key in ('SANDBASE_API_KEY','IMGBB_API_KEY')): fail(n,'Credential columns must be blank in the exported CSV')
        for field in GENERATED:
            value = row.get(field) or ''
            if not value.strip(): fail(n, f'{field} is empty')
            if CJK.search(html.unescape(value)): fail(n, f'{field} contains Chinese text')
            if re.search(r'\b(?:Xinbada|Lifeworth|ZHENGFENG)\b', value, re.I):
                fail(n, f'{field} contains inherited branding')
            if field in ('title', 'remark', 'seo_title1', 'seo_desc', 'pro_fields') and LEGACY_BRAND.search(value):
                fail(n, f'Use Yiant for the brand name in {field}')
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
        if row['pro_fields'] != expected_product_fields(row['pro_fields'], row['title']):
            fail(n, 'pro_fields must start with Product Name and use one fullwidth-colon attribute per line')
        content = row.get('content', '')
        for error in check_reports(content): fail(n,error)
        for error in faq_errors(content): fail(n, error)
        if re.search(r'\{\{.+?\}\}|\bTODO\b|\bPLACEHOLDER\b', content): fail(n, 'Unfilled content template')
        parsed = HTMLImages(content.replace(REPORT_HTML,''))
        if parsed.has_legacy_brand:
            fail(n, 'Use Yiant for the brand name in the detail content')
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
        if not parsed.images or parsed.images[0][0] != row.get('thumb'):
            fail(n, 'First detail image is not the cover')
        for url, alt in pairs + parsed.images:
            if LEGACY_BRAND.search(alt or ''): fail(n, 'Use Yiant for the brand name in image alt text')
            if not alt or CJK.search(alt): fail(n, 'Missing or non-English image alt')
            if url not in allowed: fail(n, 'Detail image has no approved asset provenance')
            if mode == 'remote' and not direct(url): fail(n, 'Image must be an ImgBB WebP Direct link')
            if mode == 'local' and not local_file(root, url): fail(n, 'Local WebP missing or unsafe path')
        entries = records.get(slug, {}).get('images', [])
        carousel = records.get(slug, {}).get('carousel_sources')
        if carousel is not None:
            if not isinstance(carousel, list) or not carousel or any(
                not isinstance(s, dict) or not s.get('url') or s.get('status') not in ('used','excluded')
                or (s.get('status') == 'excluded' and not str(s.get('reason','')).strip()) for s in carousel):
                fail(n, 'Invalid carousel source inventory')
            else:
                expected = [(i,s['url']) for i,s in enumerate(carousel,1) if s['status']=='used']
                actual = [(e.get('carousel_index'),e.get('source')) for e in entries[1:]]
                source_labels = {s['url']: s.get('source_ai_label') for s in carousel}
                for entry in entries:
                    if entry.get('source') in source_labels and entry.get('source_ai_label') != source_labels[entry['source']]:
                        fail(n, 'AI label differs between the carousel source and exported artwork')
                if actual != expected or any(not re.fullmatch('[0-9a-f]{64}',str(e.get('source_sha256',''))) for e in entries[1:]):
                    fail(n, 'Gallery does not match the original carousel source order or hashes')
        current_review = records.get(slug, {}).get('artwork_review_version') == 1
        for entry in entries + detail_entries:
            review_required = current_review and entry.get('origin') != 'source_detail'
            for error in generated_artwork_errors(entry, review_required):
                fail(n, error)
        if len(entries) != len(pairs): fail(n, 'Image manifest count differs from gallery')
        for i, (entry, pair) in enumerate(zip(entries, pairs)):
            if entry.get('brand_logo_sha256') != OFFICIAL_LOGO_HASH:
                fail(n, 'Cover and gallery assets must use the official Yiant logo')
            if entry.get('direct_url' if mode == 'remote' else 'path') != pair[0]: fail(n, 'Manifest order/URL mismatch')
            if entry.get('alt') != pair[1]: fail(n, 'Manifest alt differs from gallery')
            if not entry.get('source'): fail(n, 'Missing original image source')
            if entry.get('visual_reviewed') is not True or entry.get('product_match') is not True:
                fail(n, 'Image visual/product verification is incomplete')
            if not local_file(root, entry.get('path', '')): fail(n, 'Manifest local WebP is missing')
            asset = local_file(root, entry.get('path', ''))
            if asset:
                try:
                    with Image.open(asset) as im:
                        if im.format != 'WEBP' or im.width != im.height:
                            fail(n, 'Cover and gallery WebP images must be square')
                except OSError:
                    fail(n, 'Cannot decode gallery asset')
            if i == 0:
                if entry.get('role') != 'cover' or entry.get('origin') != 'generated_cover':
                    fail(n, 'First image must be a generated cover')
            elif (entry.get('role') != 'gallery' or entry.get('white_background') is not True
                  or entry.get('origin') not in ('source_white', 'background_edited', 'text_localized', 'source_based_illustration')):
                fail(n, 'Gallery image is not a verified source-derived white-background image')
        used_detail_urls = {url for url, _ in parsed.images}
        for entry, url in zip(detail_entries, detail_urls):
            if entry.get('brand_logo_sha256'):
                fail(n, 'Detail-only images must be exported from an unbranded source')
            if entry.get('role') not in ('detail_photo', 'production', 'material', 'application', 'drawing'):
                fail(n, 'Invalid detail asset role')
            product_illustration = (entry.get('origin') == 'source_based_illustration'
                                    and entry.get('role') in ('detail_photo', 'application', 'material'))
            if not product_illustration and entry.get('origin') not in ('source_detail', 'text_localized', 'background_edited'):
                fail(n, 'Detail asset must come from the supplied product PDF')
            if (not entry.get('source') or not entry.get('context') or not (entry.get('source_pages') or
                    (entry.get('source_panel') and str(entry['source']).startswith('https://') and re.fullmatch(r'[a-f0-9]{64}',str(entry.get('source_sha256','')))))):
                fail(n, 'Detail asset needs PDF provenance and context')
            if entry.get('visual_reviewed') is not True or entry.get('context_reviewed') is not True:
                fail(n, 'Detail asset visual/context verification is incomplete')
            if not entry.get('alt') or CJK.search(entry['alt']): fail(n, 'Detail asset needs English alt')
            if not local_file(root, entry.get('path', '')): fail(n, 'Detail asset local WebP is missing')
            if mode == 'remote' and not direct(url): fail(n, 'Detail asset must have an ImgBB WebP Direct link')
            if url not in used_detail_urls: fail(n, 'Approved detail asset is not used in the content')
        media_files = {e.get('direct_url' if mode=='remote' else 'path'):local_file(root,e.get('path',''))
                       for e in entries + detail_entries}
        for error in section_size_errors(content,media_files): fail(n,error)
        folder = root / 'images' / slug
        if folder.exists() and any(x.is_file() and x.suffix != '.webp' for x in folder.iterdir()):
            fail(n, 'Final image folder includes non-WebP files')
        for suffix in ('.fragment.html', '.html', '.txt'):
            path = root / 'details' / (slug + suffix)
            if not path.is_file() or not path.stat().st_size: fail(n, 'Missing independent detail export ' + suffix)
            elif CJK.search(html.unescape(path.read_text(encoding='utf-8'))): fail(n, 'Detail export contains Chinese text')
            elif suffix == '.txt' and LEGACY_BRAND.search(path.read_text(encoding='utf-8')):
                fail(n, 'Use Yiant for the brand name in the text export')
        fragment = root / 'details' / (slug + '.fragment.html')
        if fragment.is_file() and fragment.read_text(encoding='utf-8').strip() != content.strip():
            fail(n, 'Detail fragment differs from CSV content')
        page = root / 'details' / (slug + '.html')
        if page.is_file():
            page_text = page.read_text(encoding='utf-8')
            for error in faq_errors(page_text): fail(n, 'Standalone detail: ' + error)
            if not re.search(r'<html\b[^>]*\blang=[\"\']en[\"\']', page_text, re.I):
                fail(n, 'Standalone detail page needs lang=en')
            if not re.search(r'<meta\b[^>]*\bname=[\"\']viewport[\"\']', page_text, re.I):
                fail(n, 'Standalone detail page needs a viewport meta tag')
            for error in check_reports(page_text, standalone=True): fail(n,error)
            for error in SectionImages(page_text).layout_errors: fail(n, 'Standalone detail: ' + error)
            page_without_reports = page_text.replace(REPORT_HTML.replace('src="/uploadfile/','src="'+REPORT_HOST+'/uploadfile/'),'').replace(REPORT_HTML,'')
            page_media = HTMLImages(page_without_reports)
            if page_media.has_legacy_brand: fail(n, 'Use Yiant for the brand name in the standalone page')
            for url, alt in page_media.images:
                if mode == 'remote':
                    if url not in allowed: fail(n, 'Standalone detail image has no approved asset provenance')
                else:
                    resolved = (page.parent / url).resolve()
                    expected = {(root / value).resolve() for value in allowed}
                    if resolved not in expected or not resolved.is_file():
                        fail(n, 'Standalone detail has an invalid relative image reference')
    if original:
        old_headers, old_rows = read_csv(original)
        if headers != [h for h in old_headers if h!='scenario_image']: errors.append('Original/output column names or order differ')
        if len(old_rows) != len(rows): errors.append('Original/output row count differs')
        for n, (old, new) in enumerate(zip(old_rows, rows), 2):
            for key in old_headers:
                if key=='link' and old.get(key)!=new.get(key):
                    u=urlsplit(old.get(key,'').strip())
                    if (u.scheme not in ('http','https') or u.netloc.lower()!='detail.1688.com'
                        or not re.fullmatch(r'/offer/[1-9][0-9]{0,19}\.html/?',u.path)
                        or new.get(key)!='https://detail.1688.com'+u.path.rstrip('/')):
                        fail(n, 'Read-only input link refers to a different offer')
                if key not in GENERATED + ['SANDBASE_API_KEY','IMGBB_API_KEY','scenario_image','link'] and old.get(key) != new.get(key):
                    fail(n, f'Read-only input field changed: {key}')
    if batch_manifest:
        batch = json.loads(batch_manifest.read_text(encoding='utf-8'))
        template = Path(batch['template_path'])
        template_headers, template_rows = read_csv(template)
        if hashlib.sha256(template.read_bytes()).hexdigest() != batch['template_sha256']:
            errors.append('Batch template changed since preparation')
        if headers != [h for h in template_headers if h!='scenario_image'] or template_headers != batch['headers']:
            errors.append('Batch column names or order differ from the input template')
        ready = [p for p in batch['products'] if p['status'] == 'ready']
        if len(ready) != len(rows): errors.append('Output count differs from ready product count')
        for n, (product, row) in enumerate(zip(ready, rows), 2):
            record_path = (batch_manifest.parent / product['product_file']).resolve()
            if not record_path.is_relative_to(batch_manifest.parent.resolve()):
                fail(n, 'Product file escapes the batch directory')
                continue
            record = json.loads(record_path.read_text(encoding='utf-8'))
            if record.get('source_sha256') != product.get('source_sha256') or record.get('reviewed') is not True:
                fail(n, 'Product source or review does not match the source')
            config_number = product.get('template_row')
            config = template_rows[config_number - 2] if isinstance(config_number, int) and 2 <= config_number <= len(template_rows) + 1 else {}
            if template_rows and not config: fail(n, 'Invalid template configuration mapping')
            if batch.get('input_mode')=='link_batch':
                if record.get('verified_source_url')!=product.get('source_file') or not record.get('verified_source_url'):
                    fail(n,'Reviewed URL differs from source')
                if not records.get(row.get('file_name'),{}).get('carousel_sources'):
                    fail(n,'Link batch needs original carousel inventory')
            for key in headers:
                expected = (record.get('row', {}).get(key, '') if key in GENERATED else
                            record.get('verified_source_url', '') if key == 'link' else '' if key in ('SANDBASE_API_KEY','IMGBB_API_KEY') else config.get(key, ''))
                if key == 'pro_fields':
                    expected = expected_product_fields(expected, record['row']['title'])
                if row.get(key, '') != expected:
                    fail(n, 'Product or template configuration differs in field: ' + key)
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
