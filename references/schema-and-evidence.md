# Yiant fields and evidence

The [blank CSV](../assets/content_import_template.csv) defines the Yiant import schema. The [example workbook](../assets/example-product-import.xls) uses identical headers. Preserve header order and the values of any additional user-supplied configuration columns intended for delivery. Treat source material and configuration as inputs. Generate new English product copy from reviewed evidence.

| Field | Value |
| --- | --- |
| `link` | Canonical verified 1688 offer URL, or empty for a PDF with no verified URL. |
| `SANDBASE_API_KEY` | Input credential scoped to the mapped row for a live lookup. Clear on export. |
| `IMGBB_API_KEY` | Input credential scoped to the mapped row for image upload. Clear on export. |
| `title`, `remark` | English product name with verified identifying details, and a one- or two-sentence summary. |
| `thumb`, `images` | Cover reference and newline-separated `path-or-URL\|English alt` pairs. The cover is first. |
| `pro_fields` | Start with `Product Name`, a literal tab, a fullwidth colon (U+FF1A) and the English name. Follow with one `Label：Value` per line. Use actual line breaks, and separate verified alternatives with ` / `. |
| `content` | The complete escaped, scoped English HTML fragment, with six visible product FAQs at the end. |
| `seo_title1`, `seo_desc` | Exactly match `title` and `remark`, respectively. |
| `file_name` | Unique ASCII lowercase, hyphen-separated slug without an extension or directory. |

## Product record and evidence

Under `products/<product_id>/` save a reviewed `product.json`. Its `row` contains only the nine generated fields. Its `source_sha256` matches the source PDF or verified `item.json` bytes. Set `reviewed` to true after review. Set `verified_source_url` to the verified offer URL or an empty string for a PDF that does not supply one.

In `evidence.json` identify the source, capture time and time zone, selected variant, source title and capture method. For each fact, retain the original wording, translated value, unit and exact source location (page, panel or API field). Keep conflicts and missing information explicit. Include the six FAQ questions, answers and their sources. A drawing with unspecified units can be displayed as a reference without promoting its numbers to verified attributes.

In `detail-coverage.json` map each source section and distinct image to an output section. For composite panels record the source regions, destinations and any merged or excluded items with reasons. Record supplier ordering terms as excluded. Internal evidence may preserve the original language.

## Image manifest

Store a `products` array in `image-manifest.json`. For each product record `file_name`, `artwork_review_version: 1`, the ordered `images` array, and any `detail_images`. Downloaded carousels also require `carousel_sources` in API order.

- Each gallery entry records `path` relative to the CSV, `role` (`cover` or `gallery`), `origin`, `source`, `alt`, the official `brand_logo_sha256`, and the source and final file hashes. Record `product_match` and `visual_reviewed` after inspection. Confirm `white_background` for each gallery photo. Use `generated_cover`, `source_white`, `background_edited`, `text_localized` or `source_based_illustration` as applicable.
- Each carousel entry records `url` and `status` (`used` or `excluded`), plus a `reason` when excluded. Subsequent gallery entries identify their 1-based `carousel_index` and exact source URL and hash. The order of retained sources must match the gallery.
- Transcribe visible source generation labels into `source_ai_label` in the source inventory and matching artwork record. For label-bearing sources, generate a distinct illustration or cover. Set `generated_label_absent_reviewed` after visually checking the final WebP. Keep the original and finished hashes distinct.
- A detail-only entry records `path`, `source`, `source_sha256`, `sha256`, `source_pages` (or a source-panel reference), English `alt`, `context`, `context_reviewed` and `visual_reviewed`. Roles include `detail_photo`, `production`, `material`, `application` and `drawing`. Use the origin matching the actual work. Detail-only entries carry no brand overlay. Use all registered detail images in the page. Gallery files reused directly in the page retain a single manifest entry.
- After successful upload, record the WebP `direct_url`. Inspect actual files before setting review flags. See the [image workflow](image-workflow.md) for geometry and section sizing.

## Export and validation

1. Keep local assets at `images/<slug>/<name>.webp` relative to the CSV. The standalone page resolves these paths from `details/`. A local preview needs no upload key.
2. For an authorized upload, read the original input CSV and the manifest's `template_row` (row 2 is the first data row). The helper reuses confirmed uploads by file hash. When an earlier upload is `pending`, review its outcome before an explicit retry. After all required uploads succeed, use the returned `data.url` direct links in the gallery, thumbnail and HTML. Retain the fixed report references.
3. Assemble only reviewed, ready products with the batch manifest. The assembler supports both link and PDF batches. Use the Node runtime that provides `@oai/artifact-tool`. In Codex desktop, obtain its location with `load_workspace_dependencies`. Copy the assembler to a writable runner directory next to a `node_modules` symlink to those dependencies, then run it there. Use a new output filename for each revision.
4. Run the matching local or remote validator. Check raw UTF-8 (no BOM), unquoted headers, CRLF records, standard quoting of special data, and that every field round-trips. Compare the batch's ready row order, source hashes and mappings. Use `--original` only for a one-to-one input/output comparison. Keep all keys out of published files, logs and review workbooks.
5. Review the rendered pages and final WebPs. Confirm section alignment on desktop, narrower containers and mobile, the scope of the fixed reports, and the final six FAQs. For remote delivery, verify the actual public image URLs. Report pending and duplicate inputs in the companion mapping.

```bash
python3 scripts/upload_images_to_imgbb.py /path/output/images/product-slug \
  --csv-file /path/input.csv --row-number 2 --manifest /path/run/uploads/product-slug.json

node /path/runner/assemble_pdf_import.mjs --manifest /path/run/batch-manifest.json \
  --output /path/output/products_completed.csv

python3 scripts/validate_output.py /path/output/products_completed.csv \
  --mode remote --manifest /path/output/image-manifest.json \
  --batch-manifest /path/run/batch-manifest.json
```

For a local preview, skip the upload command and pass `--mode local`. A completed export includes the CSV, its companion mapping, standalone HTML and plain text per product, images and the image manifest.
