#!/usr/bin/env python3
"""Extract text and deduplicated embedded product-page images from a user-provided PDF."""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader


def extract(source, output, minimum_edge=120):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory is not empty; choose a new directory')
    output.mkdir(parents=True, exist_ok=True)
    images_dir = output / 'images'
    images_dir.mkdir(exist_ok=True)
    reader = PdfReader(source)
    pages = []
    entries = []
    seen = {}
    for page_number, page in enumerate(reader.pages, 1):
        pages.append({'page': page_number, 'text': page.extract_text() or ''})
        for image in page.images:
            digest = hashlib.sha256(image.data).hexdigest()
            if digest in seen:
                if page_number not in seen[digest]['pages']:
                    seen[digest]['pages'].append(page_number)
                continue
            width, height = image.image.size
            if min(width, height) < minimum_edge:
                continue
            extension = Path(image.name).suffix.lower()
            if extension not in ('.png', '.jpg', '.jpeg', '.jp2', '.tif', '.tiff', '.bmp', '.webp'):
                raise ValueError('Unsupported extracted image encoding; inspect the PDF manually')
            filename = f'image-{len(entries)+1:02d}{extension}'
            (images_dir / filename).write_bytes(image.data)
            record = {'file': 'images/' + filename, 'width': width, 'height': height,
                      'pages': [page_number], 'sha256': digest}
            entries.append(record)
            seen[digest] = record
    result = {'source_file': source.name, 'page_count': len(pages), 'images': entries}
    (output / 'image-index.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'page-text.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'page-text.txt').write_text('\n\n'.join(f'PAGE {p["page"]}\n{p["text"]}' for p in pages), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf_file', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--minimum-edge', type=int, default=120)
    args = parser.parse_args()
    if args.minimum_edge < 1:
        parser.error('--minimum-edge must be positive')
    result = extract(args.pdf_file, args.output_dir, args.minimum_edge)
    print(f'OK: {result["page_count"]} pages and {len(result["images"])} distinct images extracted; visual review is required')


if __name__ == '__main__':
    main()
