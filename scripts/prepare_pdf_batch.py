#!/usr/bin/env python3
"""Inventory a PDF batch, extract each unique file, and map template configuration."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
from extract_pdf_assets import extract

GENERATED = 'title remark thumb scenario_image images pro_fields content seo_title1 seo_desc file_name'.split()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def prepare(files, template, run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / 'batch-manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    template_unchanged = previous.get('template_sha256') == sha(template)
    with template.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not set(GENERATED).issubset(headers):
        raise ValueError('Template needs unique headers and all ten generated product columns')
    configurations = [{k: r.get(k, '') for k in headers if k not in GENERATED + ['link']} for r in rows]
    shared = len(configurations) <= 1 or all(r == configurations[0] for r in configurations)
    old = {p.get('source_sha256'): p for p in previous.get('products', []) if p.get('source_sha256')}
    products, inputs, seen = [], [], {}
    for n, source in enumerate(files, 1):
        source = source.resolve()
        entry = {'input_order': n, 'source_file': str(source), 'source_name': source.name}
        try:
            digest = sha(source)
        except OSError as exc:
            entry.update(status='failed', reason=type(exc).__name__)
            products.append(dict(entry, product_id=f'missing-{n:03d}'))
            inputs.append(entry)
            continue
        entry['source_sha256'] = digest
        if digest in seen:
            entry.update(status='duplicate', duplicate_of=seen[digest])
            inputs.append(entry)
            continue
        product_id = 'pdf-' + digest[:16]
        seen[digest] = product_id
        previous_product = old.get(digest, {})
        product = {**previous_product, **entry, 'product_id': product_id}
        folder = run_dir / 'products' / product_id
        folder.mkdir(parents=True, exist_ok=True)
        copied = folder / 'source.pdf'
        if copied.exists() and sha(copied) != digest:
            raise ValueError('Existing source PDF has a conflicting hash')
        if not copied.exists():
            shutil.copy2(source, copied)
        extracted = folder / 'extracted'
        try:
            index = extracted / 'image-index.json'
            if index.exists():
                result = json.loads(index.read_text())
                if result.get('source_sha256') != digest:
                    raise ValueError('Extraction receipt does not match source hash')
                for image in result['images']:
                    if sha(extracted / image['file']) != image['sha256']:
                        raise ValueError('Extracted image hash changed')
                if sha(extracted / 'page-text.json') != result['page_text_sha256']:
                    raise ValueError('Extracted text hash changed')
            else:
                stage = folder / 'extracted.partial'
                result = extract(copied, stage)
                result.update(source_sha256=digest, page_text_sha256=sha(stage / 'page-text.json'))
                save(stage / 'image-index.json', result)
                stage.rename(extracted)
            product.update(status=previous_product.get('status') if template_unchanged and previous_product.get('status') in ('ready', 'blocked') else 'extracted',
                           page_count=result['page_count'], image_count=len(result['images']),
                           extracted_dir=str(extracted.relative_to(run_dir)),
                           product_file=previous_product.get('product_file', f'products/{product_id}/product.json'))
            product.pop('reason', None)
        except Exception as exc:
            product.update(status='failed', reason=f'PDF extraction or receipt verification failed: {type(exc).__name__}')
        products.append(product)
        entry.update(status=product['status'], product_id=product_id)
        inputs.append(entry)
    mapping = 'shared' if shared else ('positional' if len(rows) == len(products) else 'unmapped')
    for slot, product in enumerate(products):
        product['template_row'] = (2 if rows else None) if shared else (slot + 2 if mapping == 'positional' else None)
    manifest = {'version': 1, 'input_mode': 'pdf_batch', 'template_path': str(template.resolve()),
                'template_sha256': sha(template), 'headers': headers, 'template_rows': len(rows),
                'config_mapping': mapping, 'inputs': inputs, 'products': products}
    if mapping == 'unmapped':
        manifest['mapping_error'] = 'Template configurations differ and row count does not match unique PDF inputs; explicit mapping is required.'
    save(manifest_path, manifest)
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdfs', nargs='*', type=Path)
    p.add_argument('--pdf-dir', type=Path, help='Only PDFs directly inside this explicitly selected directory')
    p.add_argument('--template-csv', type=Path, required=True)
    p.add_argument('--run-dir', type=Path, required=True)
    args = p.parse_args()
    files = list(args.pdfs)
    if args.pdf_dir:
        files.extend(sorted((x for x in args.pdf_dir.iterdir() if x.is_file() and x.suffix.lower() == '.pdf'), key=lambda x: x.name))
    if not files:
        p.error('Supply PDF files or a non-empty --pdf-dir')
    m = prepare(files, args.template_csv, args.run_dir)
    print(f"Prepared {len(m['products'])} unique PDF records; {sum(x['status']=='duplicate' for x in m['inputs'])} duplicate inputs; {sum(x['status']=='failed' for x in m['products'])} failures; configuration mapping: {m['config_mapping']}. Review facts and images before marking ready.")
    return 2 if m['config_mapping'] == 'unmapped' else 0


if __name__ == '__main__':
    raise SystemExit(main())
